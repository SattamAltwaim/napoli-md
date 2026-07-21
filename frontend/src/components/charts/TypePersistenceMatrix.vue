<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import HeatmapModule from 'highcharts/modules/heatmap'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { formatResiduePairFromIds, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

HeatmapModule(Highcharts)

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
let chart = null

const getMatrixLayout = (rowCount, columnCount, pairLabels) => {
  const rowHeight = rowCount > 80 ? 24 : rowCount > 40 ? 28 : 34
  const longestPairLabel = Math.max(...pairLabels.map(label => label.length), 0)

  return {
    chartHeight: Math.max(580, rowCount * rowHeight + 230),
    marginLeft: Math.min(240, Math.max(150, longestPairLabel * 6.5 + 24)),
    rowLabelFontSize: rowCount > 80 ? '8px' : rowCount > 40 ? '9px' : '11px',
    cellLabelFontSize: rowCount > 80 ? '8px' : rowCount > 40 ? '9px' : '11px',
    columnLabelFontSize: columnCount > 10 ? '9px' : '11px',
    columnLabelRotation: columnCount > 6 ? -35 : 0
  }
}

const buildFrameTimeline = (frames, totalFrames) => {
  const presentFrames = new Set(frames || [])
  const cells = Array.from({ length: totalFrames }, (_, index) => {
    const frame = index + 1
    const isPresent = presentFrames.has(frame)
    return `<span title="Frame ${frame}: ${isPresent ? 'Present' : 'Absent'}" style="
      display:block;
      flex:1 1 0;
      min-width:0;
      height:4px;
      background:${isPresent ? '#1976D2' : '#e5e7eb'};
    "></span>`
  }).join('')

  return `<div style="margin-top:7px;padding-top:6px;border-top:1px solid #d2d2d7;">
    <div style="font-size:13px;font-weight:700;color:#1d1d1f;margin-bottom:4px;">Frame presence</div>
    <div style="display:flex;width:280px;height:4px;overflow:hidden;background:#e5e7eb;border-radius:2px;">${cells}</div>
    <div style="display:flex;justify-content:space-between;width:280px;margin-top:2px;font-size:8px;color:#6e6e73;">
      <span>1</span><span>${totalFrames}</span>
    </div>
  </div>`
}

const updateChart = () => {
  if (!chartContainer.value) return

  const interactions = analysisStore.filteredInteractions
  if (!interactions.length) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align:center;padding:100px 20px;color:#6e6e73;font-size:19px;">No interactions above threshold.</div>'
    return
  }

  const observedTypes = new Set()
  for (const interaction of interactions) {
    for (const type of interaction.typesArray || []) {
      if (matchesSelectedTypes(type, chartUiStore.selectedInteractionTypes, INTERACTION_TYPES)) {
        observedTypes.add(type)
      }
    }
  }

  const orderedTypes = []
  for (const typeDefinition of INTERACTION_TYPES) {
    for (const type of [...observedTypes].sort()) {
      const matchesDefinition = typeDefinition.keywords.some(keyword => type.toLowerCase().includes(keyword.toLowerCase()))
      if (matchesDefinition && !orderedTypes.includes(type)) orderedTypes.push(type)
    }
  }
  const unmatchedTypes = [...observedTypes].filter(type => !orderedTypes.includes(type)).sort()
  const types = [...orderedTypes, ...unmatchedTypes]

  if (!types.length) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align:center;padding:100px 20px;color:#6e6e73;font-size:19px;">No selected interaction types are present in the filtered pairs.</div>'
    return
  }

  const sortedInteractions = [...interactions].sort((a, b) => {
    if (a.resNum1 !== b.resNum1) return a.resNum1 - b.resNum1
    return a.resNum2 - b.resNum2
  })
  const pairLabels = sortedInteractions.map(interaction => formatResiduePairFromIds(interaction.id1, interaction.id2))
  const categories = [...types, 'Overall Pair']
  const data = []
  const overallData = []

  sortedInteractions.forEach((interaction, y) => {
    types.forEach((type, x) => {
      const persistence = interaction.typePersistence?.[type]
      const isObserved = Number.isFinite(persistence)

      data.push({
        x,
        y,
        value: isObserved ? persistence : null,
        dataLabels: {
          enabled: isObserved,
          color: isObserved && persistence >= 0.58 ? '#ffffff' : '#111111'
        },
        custom: {
          pair: pairLabels[y],
          type,
          persistence: isObserved ? persistence : null,
          frameCount: isObserved ? Math.round(persistence * systemsStore.totalFrames) : 0,
          frames: interaction.typeFrames?.[type] || [],
          totalFrames: systemsStore.totalFrames,
          isOverall: false
        }
      })
    })

    overallData.push({
      x: types.length,
      y,
      value: interaction.consistency,
      dataLabels: {
        color: interaction.consistency >= 0.58 ? '#ffffff' : '#111111'
      },
      custom: {
        pair: pairLabels[y],
        type: 'Overall Pair',
        persistence: interaction.consistency,
        frameCount: interaction.frameCount,
        frames: interaction.frames || [],
        totalFrames: systemsStore.totalFrames,
        isOverall: true
      }
    })
  })

  if (chart) chart.destroy()

  const layout = getMatrixLayout(pairLabels.length, categories.length, pairLabels)
  const xTickPositions = categories.map((_, index) => index)
  const yTickPositions = pairLabels.map((_, index) => index)
  const systemName = systemsStore.currentSystem?.name || 'System'
  const chartOptions = {
    chart: {
      type: 'heatmap',
      backgroundColor: '#ffffff',
      height: layout.chartHeight,
      marginLeft: layout.marginLeft,
      spacingTop: 24,
      spacingRight: 36,
      spacingBottom: 18
    },
    title: {
      text: `${systemName} — Interaction Type Persistence Matrix`,
      margin: 32,
      style: { fontSize: '24px', fontWeight: '600', color: '#111111' }
    },
    credits: { enabled: false },
    xAxis: {
      categories,
      opposite: true,
      min: -0.5,
      max: categories.length - 0.5,
      startOnTick: false,
      endOnTick: false,
      tickPositions: xTickPositions,
      gridLineWidth: 0,
      lineWidth: 0,
      tickLength: 0,
      title: { text: null },
      labels: {
        rotation: layout.columnLabelRotation,
        formatter: function () {
          return categories[this.pos] ?? ''
        },
        style: {
          fontSize: layout.columnLabelFontSize,
          fontWeight: '600',
          color: '#111111'
        }
      },
      plotLines: [{
        value: types.length - 0.5,
        width: 2,
        color: '#111111',
        zIndex: 5
      }],
      plotBands: [{
        from: types.length - 0.5,
        to: types.length + 0.5,
        color: '#f2f2f2'
      }]
    },
    yAxis: {
      categories: pairLabels,
      reversed: true,
      min: -0.5,
      max: pairLabels.length - 0.5,
      startOnTick: false,
      endOnTick: false,
      tickPositions: yTickPositions,
      gridLineWidth: 0,
      lineWidth: 0,
      tickLength: 0,
      title: { text: null },
      labels: {
        formatter: function () {
          return pairLabels[this.pos] ?? ''
        },
        style: {
          fontSize: layout.rowLabelFontSize,
          fontWeight: '600',
          color: '#111111'
        }
      }
    },
    colorAxis: {
      min: 0,
      max: 1,
      startOnTick: false,
      endOnTick: false,
      tickPositions: [0, 0.25, 0.5, 0.75, 1],
      stops: [
        [0, '#E3F2FD'],
        [0.3, '#90CAF9'],
        [0.5, '#42A5F5'],
        [0.7, '#1976D2'],
        [1, '#0D47A1']
      ],
      labels: {
        formatter: function () {
          return `${Math.round(this.value * 100)}%`
        },
        style: { fontSize: '11px', color: '#111111' }
      }
    },
    legend: {
      enabled: true,
      align: 'center',
      verticalAlign: 'bottom',
      layout: 'horizontal',
      symbolWidth: 260,
      symbolHeight: 10,
      margin: 18,
      padding: 0,
      title: {
        text: 'Persistence',
        style: { fontSize: '12px', fontWeight: '600', color: '#111111' }
      }
    },
    plotOptions: {
      heatmap: {
        animation: false,
        borderWidth: 1,
        borderColor: '#ffffff',
        nullColor: '#f1f3f5',
        pointPadding: 1,
        states: {
          hover: {
            enabled: true,
            borderColor: '#111111',
            borderWidth: 1
          }
        },
        dataLabels: {
          enabled: true,
          formatter: function () {
            return `${Math.round(this.point.custom.persistence * 100)}%`
          },
          style: {
            fontSize: layout.cellLabelFontSize,
            fontWeight: '700',
            textOutline: 'none'
          }
        }
      }
    },
    series: [
      {
        type: 'heatmap',
        name: 'Interaction type persistence',
        data,
        showInLegend: false,
        turboThreshold: 10000
      },
      {
        type: 'heatmap',
        name: 'Overall pair conservation',
        data: overallData,
        showInLegend: false,
        turboThreshold: 10000
      }
    ],
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      outside: true,
      formatter: function () {
        const custom = this.point.custom
        if (!Number.isFinite(custom.persistence)) return false

        const percent = Math.round(custom.persistence * 100)
        const timeline = buildFrameTimeline(custom.frames, custom.totalFrames)
        return `<div style="padding:10px;">
          <div style="font-size:15px;font-weight:700;margin-bottom:6px;">${custom.pair}</div>
          <div style="margin-bottom:4px;">${custom.isOverall ? 'Overall pair conservation' : custom.type}: <b>${percent}%</b></div>
          <div style="color:#6e6e73;">Present in ${custom.frameCount} / ${custom.totalFrames} frames</div>
          ${timeline}
        </div>`
      }
    }
  }

  chart = Highcharts.chart(
    chartContainer.value,
    withExporting(chartOptions, `type-persistence-matrix-${systemsStore.currentSystem?.id || 'unknown'}`)
  )
}

onMounted(updateChart)
watch([
  () => chartUiStore.currentChartType,
  () => analysisStore.filteredInteractions.length,
  () => chartUiStore.currentThreshold,
  () => chartUiStore.selectedInteractionTypes.size,
  () => systemsStore.currentSystem?.id
], () => {
  if (chartUiStore.currentChartType === 'typePersistenceMatrix') updateChart()
}, { deep: true })
</script>

<style scoped>
.chart-wrapper { width: 100%; height: 100%; }
.chart-container { width: 100%; min-height: 580px; }
</style>
