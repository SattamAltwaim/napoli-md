<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="toggle-group">
        <span>Mean ± Std Dev</span>
        <label class="switch">
          <input type="checkbox" v-model="showStats">
          <span class="slider"></span>
        </label>
      </div>
      <div class="toggle-group">
        <span>Show Percentages</span>
        <label class="switch">
          <input type="checkbox" v-model="showPercentages">
          <span class="slider"></span>
        </label>
      </div>
    </div>
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

HighchartsMore(Highcharts)

const showStats = ref(true)
const showPercentages = ref(false)
const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
let chart = null
let hasAnimated = false

const DEFAULT_AREA_SERIES = [
  {
    key: 'totalBSA',
    label: 'Total BSA',
    unit: 'Å²',
    kind: 'absolute',
    color: '#3B6EF5',
    dashStyle: 'Solid',
    symbol: 'circle',
    percentKey: 'totalPercent'
  }
]

const fallbackColors = ['#3B6EF5', '#FF3B30', '#34C759', '#FF9500', '#5856D6', '#30B0C7']
const fallbackSymbols = ['circle', 'square', 'triangle', 'diamond']

const calculateStats = (data) => {
  if (!data.length) {
    return { mean: 0, stdDev: 0, lower: 0, upper: 0 }
  }
  const mean = data.reduce((sum, value) => sum + value, 0) / data.length
  const variance = data.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / data.length
  const stdDev = Math.sqrt(variance)
  return {
    mean,
    stdDev,
    lower: Math.max(0, mean - stdDev),
    upper: mean + stdDev
  }
}

const updateChart = () => {
  if (!chartContainer.value) return

  if (!analysisStore.areaData || analysisStore.areaData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No area data available for this system.</div>'
    return
  }

  const sortedAreaData = [...analysisStore.areaData].sort((a, b) => a.frame - b.frame) //prevents lexicographic order
  const availableSeries = (analysisStore.areaSeries?.length ? analysisStore.areaSeries : DEFAULT_AREA_SERIES)
    .filter(series => sortedAreaData.some(frame => frame[series.key] !== undefined && frame[series.key] !== null))
  const selectedKind = showPercentages.value ? 'percent' : 'absolute'
  const plottedSeries = availableSeries.filter(series => series.kind === selectedKind)
  const seriesDefinitions = plottedSeries.length ? plottedSeries : availableSeries
  const distinctUnits = [...new Set(seriesDefinitions.map(series => series.unit).filter(Boolean))]
  const yUnit = distinctUnits.length === 1 ? distinctUnits[0] : (showPercentages.value ? '%' : 'Å²')
  const categories = sortedAreaData.map(d => `${d.frame}`)

  if (chart) {
    chart.destroy()
  }

  const seriesStats = new Map()
  const seriesData = new Map()
  seriesDefinitions.forEach(series => {
    const values = sortedAreaData.map(frame => {
      const value = Number(frame[series.key])
      return Number.isFinite(value) ? value : null
    })
    const numericValues = values.filter(value => value !== null)
    seriesData.set(series.key, values)
    seriesStats.set(series.key, calculateStats(numericValues))
  })

  const buildLegendName = (baseName, color, stats) => {
    if (!showStats.value) return baseName
    return `${baseName} <span style="color:${color};font-weight:600">mean=${stats.mean.toFixed(2)} ± ${stats.stdDev.toFixed(2)}</span>`
  }

  const buildRangeSeries = (id, color, stats, baseData) => {
    if (!stats.stdDev || stats.stdDev === 0) return null
    const areaData = baseData.map((_, index) => [index, stats.lower, stats.upper])
    return {
      type: 'arearange',
      linkedTo: id,
      data: areaData,
      color,
      fillOpacity: 0.12,
      lineWidth: 0,
      enableMouseTracking: false,
      showInLegend: false,
      zIndex: 0,
      marker: {
        enabled: false
      }
    }
  }

  const chartOptions = {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      height: 650
    },
    title: {
      text: `${systemsStore.currentSystem?.name || 'System'} - Surface Area Across Frames`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: null
    },
    credits: {
      enabled: false
    },
    xAxis: {
      categories: categories,
      title: {
        text: chartUiStore.timeUnit ? `Time (${chartUiStore.timeUnit})` : 'Frame',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      }
    },
    yAxis: {
      title: {
        text: showPercentages.value ? 'Surface Area (%)' : 'Surface Area (Å²)',
        style: {
          fontSize: '15px',
          fontWeight: '600',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '12px',
          fontWeight: '500',
          color: '#1d1d1f'
        }
      }
    },
    legend: {
      align: 'right',
      verticalAlign: 'middle',
      layout: 'vertical',
      width: 260,
      x: -8,
      y: 0,
      itemDistance: 12,
      itemMarginTop: 6,
      itemMarginBottom: 6,
      useHTML: true,
      itemStyle: {
        fontSize: '12px',
        fontWeight: '500',
        color: '#1d1d1f',
        lineHeight: '16px'
      }
    },
    plotOptions: {
      line: {
        animation: hasAnimated ? false : { duration: 800 },
        lineWidth: 2,
        marker: {
          enabled: true,
          radius: 3,
          lineWidth: 1,
          lineColor: '#ffffff'
        },
        states: {
          hover: {
            lineWidth: 3
          }
        }
      }
    },
    series: seriesDefinitions.map((series, index) => {
      const color = series.color || fallbackColors[index % fallbackColors.length]
      const stats = seriesStats.get(series.key)
      return {
        id: `${series.key}-line`,
        name: buildLegendName(`${series.label} (${series.unit || yUnit})`, color, stats),
        data: seriesData.get(series.key),
        color,
        dashStyle: series.dashStyle || 'Solid',
        zIndex: 2,
        marker: {
          symbol: series.symbol || fallbackSymbols[index % fallbackSymbols.length]
        },
        custom: series
      }
    }).concat(
      showStats.value
        ? seriesDefinitions.map((series, index) => {
          const color = series.color || fallbackColors[index % fallbackColors.length]
          return buildRangeSeries(
            `${series.key}-line`,
            color,
            seriesStats.get(series.key),
            seriesData.get(series.key)
          )
        }).filter(Boolean)
        : []
    ),
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      shared: true,
      useHTML: true,
      formatter: function() {
        let html = `<div style="padding: 10px;">`
        html += `<div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">${this.x}</div>`
        
        const sortedPoints = [...this.points].sort((a, b) => b.y - a.y)
        sortedPoints.forEach(point => {
          const frameIndex = point.point?.index ?? 0
          const frameData = sortedAreaData[frameIndex]
          const seriesMeta = point.series.userOptions.custom || {}
          const unit = seriesMeta.unit || yUnit
          const valueText = point.y === null || point.y === undefined
            ? 'n/a'
            : `${point.y.toFixed(2)} ${unit}`
          const percentValue = !showPercentages.value && frameData && seriesMeta.percentKey
            ? Number(frameData[seriesMeta.percentKey])
            : null
          const percentText = percentValue !== null && percentValue !== undefined && Number.isFinite(percentValue)
            ? ` (${percentValue.toFixed(2)}%)`
            : ''

          html += `
            <div style="margin-bottom: 4px;">
              <span style="color: ${point.color}; font-weight: 600;">●</span>
              <span style="color: #1d1d1f;">${seriesMeta.label || point.series.name}: </span>
              <span style="color: #1d1d1f; font-weight: 600;">${valueText}${percentText}</span>
            </div>
          `
        })
        html += '</div>'
        return html
      }
    }
  }

  const systemName = systemsStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `buried-surface-area-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
  hasAnimated = true
}

onMounted(() => {
  updateChart()
})

watch([
  () => chartUiStore.currentChartType,
  () => analysisStore.areaData.length,
  () => analysisStore.areaSeries.length,
  () => showStats.value,
  () => showPercentages.value,
  () => chartUiStore.timeUnit
], () => {
  if (chartUiStore.currentChartType === 'area') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.chart-toolbar {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 4px 0;
  gap: 12px;
}

.toggle-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 200px;
  font-size: 16px;
  font-weight: 500;
  color: #1d1d1f;
}

.switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 22px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #d2d2d7;
  transition: .2s;
  border-radius: 22px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .2s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

input:checked + .slider {
  background-color: #3B6EF5;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.chart-container {
  flex: 1;
  width: 100%;
  height: calc(100% - 40px);
}
</style>
