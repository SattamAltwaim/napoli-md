<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { formatResiduePairFromIds, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
let chart = null

const markerRadius = (persistence) => 5 + 20 * Math.sqrt(persistence)

const persistenceColor = (persistence) => {
  if (persistence >= 0.9) return '#0D47A1'
  if (persistence >= 0.7) return '#1976D2'
  if (persistence >= 0.5) return '#42A5F5'
  if (persistence >= 0.3) return '#90CAF9'
  return '#BBDEFB'
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
      if (persistence === undefined || persistence === null) return

      data.push({
        x,
        y,
        color: persistenceColor(persistence),
        marker: {
          radius: markerRadius(persistence)
        },
        custom: {
          pair: pairLabels[y],
          type,
          persistence,
          frameCount: Math.round(persistence * systemsStore.totalFrames),
          frames: interaction.typeFrames?.[type] || [],
          totalFrames: systemsStore.totalFrames,
          isOverall: false
        }
      })
    })

    overallData.push({
      x: types.length,
      y,
      color: persistenceColor(interaction.consistency),
      marker: {
        radius: markerRadius(interaction.consistency),
        symbol: 'diamond'
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

  const dynamicHeight = Math.max(580, pairLabels.length * 46 + 250)
  const systemName = systemsStore.currentSystem?.name || 'System'
  const chartOptions = {
    chart: {
      type: 'scatter',
      backgroundColor: '#ffffff',
      height: dynamicHeight,
      marginLeft: 190,
      spacingTop: 30,
      spacingBottom: 25
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
      tickmarkPlacement: 'between',
      gridLineWidth: 1,
      gridLineColor: '#d9d9d9',
      lineColor: '#111111',
      tickColor: '#111111',
      title: { text: null },
      labels: {
        rotation: -35,
        style: { fontSize: '11px', fontWeight: '600', color: '#111111' }
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
      tickmarkPlacement: 'between',
      gridLineWidth: 1,
      gridLineColor: '#d9d9d9',
      lineWidth: 1,
      lineColor: '#111111',
      tickWidth: 1,
      tickColor: '#111111',
      title: { text: null },
      labels: {
        style: { fontSize: '11px', fontWeight: '600', color: '#111111' }
      }
    },
    legend: { enabled: false },
    plotOptions: {
      scatter: {
        animation: false,
        marker: {
          lineWidth: 1.5,
          lineColor: '#ffffff',
          states: {
            hover: {
              enabled: true,
              lineWidth: 2,
              lineColor: '#111111'
            }
          }
        },
        dataLabels: {
          enabled: true,
          formatter: function () {
            return `${Math.round(this.point.custom.persistence * 100)}%`
          },
          style: {
            fontSize: '11px',
            fontWeight: '700',
            color: '#111111',
            textOutline: '2px #ffffff'
          }
        }
      }
    },
    series: [
      {
        type: 'scatter',
        name: 'Interaction type persistence',
        data,
        turboThreshold: 10000
      },
      {
        type: 'scatter',
        name: 'Overall pair conservation',
        data: overallData,
        turboThreshold: 10000
      }
    ],
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      formatter: function () {
        const custom = this.point.custom
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
