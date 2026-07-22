<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import HighchartsMore from 'highcharts/highcharts-more'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { formatResiduePairFromIds, getInteractionBaseColor, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'

HighchartsMore(Highcharts)

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
let chart = null

const chooseChangingResidueSide = (interactions) => {
  const ids1 = new Set(interactions.map(interaction => interaction.id1).filter(Boolean))
  const ids2 = new Set(interactions.map(interaction => interaction.id2).filter(Boolean))
  return ids1.size >= ids2.size ? 'id1' : 'id2'
}

const getBubbleSizing = (pointCount) => {
  if (pointCount > 90) return { minSize: 4, maxSize: 14, labelFontSize: '7px' }
  if (pointCount > 60) return { minSize: 5, maxSize: 16, labelFontSize: '7px' }
  if (pointCount > 35) return { minSize: 6, maxSize: 20, labelFontSize: '8px' }
  if (pointCount > 20) return { minSize: 7, maxSize: 24, labelFontSize: '8px' }
  return { minSize: 8, maxSize: 30, labelFontSize: '9px' }
}

const spreadOverlappingPoints = (points) => {
  const groups = new Map()
  for (const point of points) {
    const key = `${point.x.toFixed(4)}:${point.y.toFixed(4)}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(point)
  }

  for (const group of groups.values()) {
    if (group.length < 2) continue

    group.sort((a, b) => a.name.localeCompare(b.name))
    const trueX = group[0].x
    const trueY = group[0].y
    const xDirection = trueX >= 92 ? -1 : trueX <= 8 ? 1 : 0
    const yDirection = trueY >= 92 ? -1 : trueY <= 8 ? 1 : 0
    const preferredX = xDirection || 1
    const preferredY = yDirection || 1

    group.forEach((point, index) => {
      if (index === 0) return

      const ring = Math.ceil(index / 4)
      const slot = (index - 1) % 4
      const distance = 8 * ring
      const fallbackOffsets = [
        [-distance, 0],
        [distance, 0],
        [0, -distance],
        [0, distance]
      ]
      const cornerOffsets = [
        [preferredX * distance, 0],
        [0, preferredY * distance],
        [preferredX * distance, preferredY * distance],
        [preferredX * distance * 2, preferredY * distance]
      ]
      const [dx, dy] = xDirection || yDirection
        ? cornerOffsets[slot]
        : fallbackOffsets[slot]

      point.x = Math.max(0, Math.min(100, trueX + dx))
      point.y = Math.max(0, Math.min(100, trueY + dy))
      point.custom.displaced = true
    })
  }

}

const buildFrameTimeline = (frames, totalFrames) => {
  const presentFrames = new Set(frames || [])
  const cells = Array.from({ length: totalFrames }, (_, index) => {
    const frame = index + 1
    const isPresent = presentFrames.has(frame)
    return `<span title="Frame ${frame}: ${isPresent ? 'Present' : 'Absent'}" style="
      display:block;flex:1 1 0;min-width:0;height:4px;
      background:${isPresent ? '#1976D2' : '#e5e7eb'};
    "></span>`
  }).join('')

  return `<div style="margin-top:8px;padding-top:7px;border-top:1px solid #d2d2d7;">
    <div style="font-size:12px;font-weight:700;color:#1d1d1f;margin-bottom:4px;">Frame presence</div>
    <div style="display:flex;width:280px;height:4px;overflow:hidden;background:#e5e7eb;border-radius:2px;">${cells}</div>
    <div style="display:flex;justify-content:space-between;width:280px;margin-top:2px;font-size:8px;color:#6e6e73;">
      <span>1</span><span>${totalFrames}</span>
    </div>
  </div>`
}

const updateChart = () => {
  if (!chartContainer.value) return

  const totalFrames = systemsStore.totalFrames || 1
  const selectedTypes = chartUiStore.selectedInteractionTypes
  if (!analysisStore.interactions.length || selectedTypes.size === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align:center;padding:100px 20px;color:#6e6e73;font-size:19px;">Select at least one interaction type to build the landscape.</div>'
    return
  }

  const points = []
  const labelSide = chooseChangingResidueSide(analysisStore.interactions)
  for (const interaction of analysisStore.interactions) {
    const allTypeEntries = (interaction.typesArray || [])
      .map(type => ({
        type,
        frames: interaction.typeFrames?.[type] || [],
        persistence: interaction.typePersistence?.[type] || 0
      }))
    const contactFrames = new Set(allTypeEntries.flatMap(entry => entry.frames))
    const pairPersistence = contactFrames.size / totalFrames
    const pair = formatResiduePairFromIds(interaction.id1, interaction.id2)
    const residueLabel = interaction[labelSide] || interaction.id1 || interaction.id2 || pair
    const selectedEntries = allTypeEntries
      .filter(entry => matchesSelectedTypes(entry.type, selectedTypes, INTERACTION_TYPES))
      .sort((a, b) => b.persistence - a.persistence || a.type.localeCompare(b.type))

    selectedEntries.forEach((entry, index) => {
      const typeExpression = contactFrames.size ? entry.frames.length / contactFrames.size : 0
      points.push({
        x: pairPersistence * 100,
        y: typeExpression * 100,
        z: entry.persistence * 100,
        name: residueLabel,
        color: getInteractionBaseColor(entry.type),
        marker: {
          lineWidth: entry.type === 'Clashes' ? 4 : 1.5,
          lineColor: entry.type === 'Clashes' ? '#D32F2F' : '#ffffff'
        },
        custom: {
          pair,
          residueLabel,
          interactionType: entry.type,
          pairPersistence,
          typeExpression,
          typePersistence: entry.persistence,
          contactFrameCount: contactFrames.size,
          typeFrameCount: entry.frames.length,
          frames: entry.frames,
          totalFrames,
          primaryLabel: index === 0
        }
      })
    })
  }

  if (!points.length) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align:center;padding:100px 20px;color:#6e6e73;font-size:19px;">No residue pairs contain the selected interaction types.</div>'
    return
  }

  spreadOverlappingPoints(points)
  const bubbleSizing = getBubbleSizing(points.length)

  for (const point of points) {
    const normalizedPersistence = Math.max(0, Math.min(1, point.custom.typePersistence))
    const bubbleDiameter = bubbleSizing.minSize +
      (bubbleSizing.maxSize - bubbleSizing.minSize) * Math.sqrt(normalizedPersistence)

    point.labelrank = point.custom.typePersistence * 1000 + point.custom.pairPersistence * 100
    point.dataLabels = {
      enabled: true,
      y: -(Math.round(bubbleDiameter / 2) + 4)
    }
  }

  if (chart) chart.destroy()

  const systemName = systemsStore.currentSystem?.name || 'System'
  const seriesByType = new Map()
  for (const point of points) {
    const type = point.custom.interactionType
    if (!seriesByType.has(type)) seriesByType.set(type, [])
    seriesByType.get(type).push(point)
  }
  const series = [...seriesByType.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([type, typePoints]) => ({
      type: 'bubble',
      name: type,
      color: getInteractionBaseColor(type),
      data: typePoints,
      minSize: bubbleSizing.minSize,
      maxSize: bubbleSizing.maxSize,
      sizeBy: 'area',
      zMin: 0,
      zMax: 100,
      turboThreshold: 10000
    }))

  const chartOptions = {
    chart: {
      type: 'bubble',
      backgroundColor: '#ffffff',
      height: 760,
      spacingTop: 35,
      spacingRight: 45,
      spacingBottom: 35
    },
    title: {
      text: `${systemName} — Interaction Character Map`,
      margin: 12,
      style: { fontSize: '24px', fontWeight: '600', color: '#111111' }
    },
    subtitle: {
      text: 'One bubble per residue–interaction type · Bubble size = trajectory persistence · Label = changing residue',
      style: { fontSize: '13px', color: '#6e6e73' }
    },
    credits: { enabled: false },
    xAxis: {
      min: 0,
      max: 105,
      tickInterval: 10,
      gridLineWidth: 1,
      gridLineColor: '#e5e7eb',
      lineColor: '#111111',
      tickColor: '#111111',
      title: {
        text: 'Pair Persistence (% of frames)',
        style: { fontSize: '14px', fontWeight: '600', color: '#111111' }
      },
      labels: { format: '{value}%', style: { color: '#111111' } }
    },
    yAxis: {
      min: 0,
      max: 105,
      tickInterval: 10,
      gridLineWidth: 1,
      gridLineColor: '#e5e7eb',
      lineWidth: 1,
      lineColor: '#111111',
      tickWidth: 1,
      tickColor: '#111111',
      title: {
        text: 'Interaction Expression (% of pair-contact frames)',
        style: { fontSize: '14px', fontWeight: '600', color: '#111111' }
      },
      labels: { format: '{value}%', style: { color: '#111111' } }
    },
    legend: {
      enabled: true,
      align: 'center',
      verticalAlign: 'bottom',
      layout: 'horizontal',
      itemStyle: { fontSize: '11px', fontWeight: '600', color: '#111111' }
    },
    plotOptions: {
      bubble: {
        animation: false,
        marker: {
          fillOpacity: 0.72,
          states: {
            hover: {
              enabled: true,
              lineWidthPlus: 2,
              radiusPlus: 2
            }
          }
        },
        dataLabels: {
          enabled: true,
          align: 'center',
          allowOverlap: false,
          backgroundColor: 'transparent',
          borderWidth: 0,
          crop: false,
          overflow: 'allow',
          padding: 0,
          useHTML: false,
          formatter: function () {
            return this.point.name
          },
          style: {
            fontSize: bubbleSizing.labelFontSize,
            fontWeight: '600',
            color: '#111111',
            textOutline: '2px #ffffff'
          }
        }
      }
    },
    series,
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      useHTML: true,
      formatter: function () {
        const custom = this.point.custom
        return `<div style="padding:10px;min-width:290px;">
          <div style="font-size:15px;font-weight:700;margin-bottom:6px;">${custom.pair}</div>
          <div style="font-weight:700;color:${getInteractionBaseColor(custom.interactionType)};">${custom.interactionType}</div>
          <div style="margin-top:5px;">Pair persistence: <b>${Math.round(custom.pairPersistence * 100)}%</b></div>
          <div>Interaction expression: <b>${Math.round(custom.typeExpression * 100)}%</b> of pair-contact frames</div>
          <div>Trajectory persistence: <b>${Math.round(custom.typePersistence * 100)}%</b> (${custom.typeFrameCount} of ${custom.totalFrames} frames)</div>
          ${buildFrameTimeline(custom.frames, custom.totalFrames)}
        </div>`
      }
    }
  }

  chart = Highcharts.chart(
    chartContainer.value,
    withExporting(chartOptions, `interaction-character-map-${systemsStore.currentSystem?.id || 'unknown'}`)
  )
}

onMounted(updateChart)
watch([
  () => chartUiStore.currentChartType,
  () => analysisStore.interactions.length,
  () => chartUiStore.selectedInteractionTypes.size,
  () => systemsStore.currentSystem?.id
], () => {
  if (chartUiStore.currentChartType === 'dynamicContactLandscape') updateChart()
}, { deep: true })
</script>

<style scoped>
.chart-wrapper { width: 100%; height: 100%; }
.chart-container { width: 100%; min-height: 760px; }
</style>
