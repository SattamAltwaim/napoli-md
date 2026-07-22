<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import SankeyModule from 'highcharts/modules/sankey'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { getInteractionBaseColor, getInteractionColorArray, formatResidueId, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

SankeyModule(Highcharts)

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
let chart = null
const hiddenLegendTypes = new Set()

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

  const links = []
  const nodes = new Map()
  const availableTypes = new Set()

  for (const row of interactions) {
    const source = formatResidueId(row.resName1, row.resNum1, row.chain1)
    const target = formatResidueId(row.resName2, row.resNum2, row.chain2)
    if (!source || !target) continue

    for (const type of row.typesArray || []) {
      if (!matchesSelectedTypes(type, chartUiStore.selectedInteractionTypes, INTERACTION_TYPES)) continue
      availableTypes.add(type)
      if (hiddenLegendTypes.has(type)) continue

      const persistence = row.typePersistence?.[type] ?? row.consistency ?? 0
      if (persistence <= 0) continue

      const color = getInteractionBaseColor(type)
      const colorArray = getInteractionColorArray(type)
      const linkColor = `rgba(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]}, 0.68)`
      const weight = Math.max(1, Math.round(persistence * 100))
      const custom = {
        pair: `${source} ↔ ${target}`,
        type,
        conservation: Math.round(persistence * 100)
      }

      nodes.set(source, {
        id: source,
        name: source,
        column: 0,
        color: '#2563EB',
        custom: { role: `Chain ${row.chain1} residue` }
      })
      nodes.set(target, {
        id: target,
        name: target,
        column: 1,
        color: '#6B7280',
        custom: { role: `Chain ${row.chain2} residue` }
      })

      links.push({ from: source, to: target, weight, color: linkColor, custom })
    }
  }

  for (const type of hiddenLegendTypes) {
    if (!availableTypes.has(type)) hiddenLegendTypes.delete(type)
  }

  if (chart) chart.destroy()

  const sourceNodeCount = [...nodes.values()].filter(node => node.column === 0).length
  const dynamicHeight = Math.max(720, Math.min(1040, sourceNodeCount * 34 + 190))
  const systemName = systemsStore.currentSystem?.name || 'System'
  const chartOptions = {
    chart: {
      backgroundColor: 'transparent',
      height: dynamicHeight,
      spacingTop: 24,
      spacingRight: 28,
      spacingBottom: 24,
      spacingLeft: 28,
      events: {
        render: function () {
          const sankeySeries = this.series.find(series => series.type === 'sankey')
          for (const point of sankeySeries?.points || []) {
            point.graphic?.attr({
              stroke: '#ffffff',
              'stroke-width': 1.25,
              'stroke-linejoin': 'round'
            })
          }
        }
      }
    },
    title: {
      text: `${systemName} — Interaction Sankey Diagram`,
      margin: 20,
      style: { fontSize: '22px', fontWeight: '600', color: '#111111' }
    },
    subtitle: { text: null },
    credits: { enabled: false },
    xAxis: { visible: false },
    yAxis: { visible: false, title: { text: null } },
    legend: {
      enabled: true,
      align: 'right',
      verticalAlign: 'middle',
      layout: 'vertical',
      margin: 20,
      padding: 0,
      itemMarginTop: 3,
      itemMarginBottom: 3,
      title: {
        text: 'Interaction type',
        style: { fontSize: '11px', fontWeight: '600', color: '#4b5563' }
      },
      itemStyle: { fontSize: '11px', fontWeight: '500', color: '#111111' },
      itemHoverStyle: { color: '#000000' },
      itemHiddenStyle: { color: '#b6b6ba' },
      symbolRadius: 6
    },
    plotOptions: {
      series: {
        animation: false,
        states: {
          inactive: { opacity: 0.18 }
        },
        events: {
          legendItemClick: function () {
            const type = this.options.custom?.interactionType
            if (!type) return false

            if (hiddenLegendTypes.has(type)) hiddenLegendTypes.delete(type)
            else hiddenLegendTypes.add(type)

            setTimeout(updateChart, 0)
            return false
          }
        }
      }
    },
    series: [
      {
        type: 'sankey',
        name: 'Interaction flow',
        showInLegend: false,
        data: links,
        nodes: Array.from(nodes.values()),
        nodeWidth: 18,
        nodePadding: 0,
        borderWidth: 1,
        borderColor: '#ffffff',
        curveFactor: 0,
        linkOpacity: 0.82,
        minLinkWidth: 3,
        dataLabels: {
          enabled: true,
          nodeFormat: '{point.name}',
          padding: 0,
          allowOverlap: false,
          style: {
            fontSize: '10px',
            fontWeight: '600',
            color: '#111111',
            textOutline: '2px rgba(255,255,255,0.95)',
            fontVariantNumeric: 'tabular-nums'
          }
        }
      },
      ...[...availableTypes]
        .sort((a, b) => a.localeCompare(b))
        .map(type => ({
          type: 'scatter',
          name: type,
          color: getInteractionBaseColor(type),
          data: [],
          showInLegend: true,
          visible: !hiddenLegendTypes.has(type),
          enableMouseTracking: false,
          marker: { symbol: 'circle', radius: 6 },
          custom: { interactionType: type }
        }))
    ],
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.98)',
      borderRadius: 8,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      outside: true,
      nodeFormatter: function () {
        const role = this.options.custom?.role || 'Node'
        const links = [...(this.linksFrom || []), ...(this.linksTo || [])]
        return `<div style="padding:10px;">
          <div style="font-size:15px;font-weight:700;margin-bottom:4px;">${this.name}</div>
          <div style="color:#6e6e73;">${role} · ${links.length} flows</div>
        </div>`
      },
      pointFormatter: function () {
        const custom = this.options.custom
        if (!custom) return ''
        const color = getInteractionBaseColor(custom.type)
        return `<div style="padding:12px;">
          <div style="font-size:14px;font-weight:700;margin-bottom:6px;">${custom.pair}</div>
          <div><span style="color:${color};font-weight:700;">&#9679;</span> ${custom.type}</div>
          <div style="margin-top:5px;">Type conservation: <b>${custom.conservation}%</b></div>
        </div>`
      }
    }
  }

  chart = Highcharts.chart(
    chartContainer.value,
    withExporting(chartOptions, `interaction-sankey-${systemsStore.currentSystem?.id || 'unknown'}`)
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
  if (chartUiStore.currentChartType === 'interactionSankey') updateChart()
}, { deep: true })
</script>

<style scoped>
.chart-wrapper { width: 100%; height: 100%; }
.chart-container { width: 100%; min-height: 760px; }
</style>
