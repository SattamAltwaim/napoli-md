/**
 * Static data service for the bundled 8CGK / 6UQ simulated trajectory.
 * The source files are split by frame, but this module returns the same
 * payload shapes the COCOMAPS-MD frontend expects.
 */

const DATA_ROOT = '/data/simulated_trajectory_8cgk_6UQ'
const SYSTEM_ID = 'simulated-trajectory-8cgk-6uq'

const FINAL_FILE_SUFFIX = '_final_file.csv'
const MANIFEST_PATH = `${DATA_ROOT}/simulation_manifest.json`
const SUMMARY_PATH = `${DATA_ROOT}/trajectory_summary.csv`

const TREND_KEYS = {
  hBond: 'H-bonds',
  chOn: 'CH-O/N bonds',
  polarVdw: 'Polar vdW contacts',
  chPi: 'CH-\u03c0 interactions',
  proximal: 'Proximal contacts'
}

const TYPE_ORDER = [
  'H-bond',
  'CH-O/N bond',
  'Polar vdW contact',
  'CH-\u03c0 Interaction',
  'Proximal contact'
]

function parseCSV(text) {
  const cleaned = text.replace(/^\uFEFF/, '').trim()
  if (!cleaned) return []

  const lines = cleaned.split(/\r?\n/)
  if (lines.length < 2) return []

  const headers = lines[0].split(',').map(header => header.trim())
  return lines.slice(1).filter(Boolean).map(line => {
    const values = line.split(',')
    const obj = {}
    headers.forEach((header, index) => {
      obj[header] = (values[index] || '').trim()
    })
    return obj
  })
}

function parseNumber(value, fallback = 0) {
  if (value === undefined || value === null || value === '') return fallback
  const parsed = Number(String(value).replace('*', '').trim())
  return Number.isFinite(parsed) ? parsed : fallback
}

function parseInteger(value, fallback = 0) {
  const parsed = parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : fallback
}

function formatResidueId(resName, resNum, chain) {
  if (!resName || !resNum || !chain) return ''
  return `${String(resName).trim()}${parseInteger(resNum)}_${String(chain).trim()}`
}

function normalizeInteractionType(rawType) {
  const cleaned = String(rawType || '')
    .replaceAll('*', '')
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleaned) return ''

  const lower = cleaned.toLowerCase()
  if (lower === 'h-bond') return 'H-bond'
  if (lower === 'ch-o/n bond') return 'CH-O/N bond'
  if (lower === 'polar vdw contact') return 'Polar vdW contact'
  if (/^ch-\s*\u03c0 interaction$/i.test(cleaned)) return 'CH-\u03c0 Interaction'
  if (lower === 'proximal contact') return 'Proximal contact'
  return cleaned
}

function splitInteractionTypes(typesString) {
  return String(typesString || '')
    .split(';')
    .map(normalizeInteractionType)
    .filter(Boolean)
}

function uniqueSortedFrames(frameSet) {
  return [...frameSet].sort((a, b) => a - b)
}

function sortTypes(types) {
  return [...types].sort((a, b) => {
    const indexA = TYPE_ORDER.indexOf(a)
    const indexB = TYPE_ORDER.indexOf(b)
    if (indexA === -1 && indexB === -1) return a.localeCompare(b)
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })
}

function getLigandCode(manifest) {
  return String(manifest?.source?.ligand || '6UQ').split('-')[0]
}

function getInteractingChains(manifest) {
  const chains = String(manifest?.source?.interacting_chains || 'a l')
    .split(/\s+/)
    .filter(Boolean)
  return chains.length ? chains : ['a', 'l']
}

function getFrameNumbers(manifest) {
  const summaryFrames = manifest?.frame_summaries
    ?.map(frame => parseInteger(frame.frame))
    .filter(frame => frame > 0)

  if (summaryFrames?.length) return summaryFrames

  const frameCount = parseInteger(manifest?.simulation?.frames, 0)
  return Array.from({ length: frameCount }, (_, index) => index + 1)
}

function getFrameDirectory(frameNumber) {
  return `frame_${String(frameNumber).padStart(2, '0')}`
}

function getNapoliBaseName(manifest) {
  const pdb = String(manifest?.source?.pdb || '8cgk').toLowerCase()
  const ligandChain = String(manifest?.source?.ligand_chain || 'a')
  const ligandCode = getLigandCode(manifest)
  const chains = getInteractingChains(manifest)
  return `${pdb}_optimized.pd_h.pdb_${ligandChain}_${ligandCode}_['${chains[0]}', '${chains[1]}']`
}

function getFrameFilePath(manifest, frameNumber, suffix) {
  const fileName = `${getNapoliBaseName(manifest)}${suffix}`
  return `${DATA_ROOT}/${getFrameDirectory(frameNumber)}/${encodeURI(fileName)}`
}

function getSystemName(manifest) {
  const pdb = String(manifest?.source?.pdb || '8CGK').toUpperCase()
  const ligand = getLigandCode(manifest)
  return `${pdb} / ${ligand} Simulated Trajectory`
}

function buildSystem(manifest) {
  const ligand = getLigandCode(manifest)
  const chains = getInteractingChains(manifest)
  const frames = getFrameNumbers(manifest).length

  return {
    id: SYSTEM_ID,
    name: getSystemName(manifest),
    frames,
    chain1: chains.join('/'),
    chain2: ligand,
    jobId: SYSTEM_ID
  }
}

let textCache = {}
let manifestPromise = null
let summaryPromise = null
let frameRowsPromise = null

async function fetchText(path) {
  if (Object.prototype.hasOwnProperty.call(textCache, path)) return textCache[path]

  const res = await fetch(path)
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`)

  const text = await res.text()
  textCache[path] = text
  return text
}

async function fetchJSON(path) {
  const text = await fetchText(path)
  return JSON.parse(text)
}

async function getManifest() {
  if (!manifestPromise) manifestPromise = fetchJSON(MANIFEST_PATH)
  return manifestPromise
}

async function getSummaryRows() {
  if (!summaryPromise) {
    summaryPromise = fetchText(SUMMARY_PATH).then(parseCSV)
  }
  return summaryPromise
}

async function getFrameRows() {
  if (frameRowsPromise) return frameRowsPromise

  frameRowsPromise = (async () => {
    const manifest = await getManifest()
    const frameNumbers = getFrameNumbers(manifest)

    return Promise.all(frameNumbers.map(async frame => {
      const path = getFrameFilePath(manifest, frame, FINAL_FILE_SUFFIX)
      const rows = parseCSV(await fetchText(path))
      return { frame, rows }
    }))
  })()

  return frameRowsPromise
}

function addInteractionFrame(entry, type, frame) {
  entry.frames.add(frame)
  entry.types.add(type)

  if (!entry.typeFrames[type]) entry.typeFrames[type] = new Set()
  entry.typeFrames[type].add(frame)
}

function buildInteractionAggregate(frameRows, totalFrames) {
  const interactionMap = {}

  for (const frameData of frameRows) {
    for (const row of frameData.rows) {
      const resName1 = row['NA/Protein Res Name']
      const resNum1 = row['NA/Protein Res Number']
      const chain1 = row['NA/Protein Chain']
      const resName2 = row['Ligand Res Name']
      const resNum2 = row['Ligand Res Number']
      const chain2 = row['Ligand Chain']
      const types = splitInteractionTypes(row['Type of Interactions'])

      if (!types.length) continue

      const id1 = formatResidueId(resName1, resNum1, chain1)
      const id2 = formatResidueId(resName2, resNum2, chain2)
      if (!id1 || !id2) continue

      const key = `${id1}__${id2}`
      if (!interactionMap[key]) {
        interactionMap[key] = {
          resName1,
          resNum1: parseInteger(resNum1),
          chain1,
          id1,
          resName2,
          resNum2: parseInteger(resNum2),
          chain2,
          id2,
          frames: new Set(),
          types: new Set(),
          typeFrames: {}
        }
      }

      const entry = interactionMap[key]
      for (const type of new Set(types)) {
        addInteractionFrame(entry, type, frameData.frame)
      }
    }
  }

  const interactions = Object.values(interactionMap).map(entry => {
    const frameNumbers = uniqueSortedFrames(entry.frames)
    const typesArray = sortTypes(entry.types)
    const typePersistence = {}
    const typeFrames = {}

    for (const type of typesArray) {
      const frames = uniqueSortedFrames(entry.typeFrames[type] || new Set())
      typeFrames[type] = frames
      typePersistence[type] = totalFrames ? frames.length / totalFrames : 0
    }

    return {
      resName1: entry.resName1,
      resNum1: entry.resNum1,
      chain1: entry.chain1,
      id1: entry.id1,
      resName2: entry.resName2,
      resNum2: entry.resNum2,
      chain2: entry.chain2,
      id2: entry.id2,
      frameCount: frameNumbers.length,
      consistency: totalFrames ? frameNumbers.length / totalFrames : 0,
      types: typesArray.join('; '),
      typesArray,
      typePersistence,
      frames: frameNumbers,
      typeFrames
    }
  })

  interactions.sort((a, b) => {
    if (b.consistency !== a.consistency) return b.consistency - a.consistency
    return a.id1.localeCompare(b.id1, undefined, { numeric: true })
  })

  return interactions
}

function buildTrendPayload(summaryRows) {
  const frameNumbers = summaryRows.map(row => parseInteger(row.frame)).filter(frame => frame > 0)

  return {
    frameNumbers,
    trends: {
      [TREND_KEYS.hBond]: summaryRows.map(row => parseInteger(row.h_bond) + parseInteger(row.h_bond_star)),
      [TREND_KEYS.chOn]: summaryRows.map(row => parseInteger(row.ch_o_n) + parseInteger(row.ch_o_n_star)),
      [TREND_KEYS.polarVdw]: summaryRows.map(row => parseInteger(row.polar_vdw) + parseInteger(row.polar_vdw_star)),
      [TREND_KEYS.chPi]: summaryRows.map(row => parseInteger(row.ch_pi)),
      [TREND_KEYS.proximal]: summaryRows.map(row => parseInteger(row.proximal_only))
    }
  }
}

function buildAreaFrames(summaryRows) {
  return summaryRows.map(row => ({
    frame: parseInteger(row.frame),
    totalBSA: parseNumber(row.ligand_bsa_a2),
    polarBSA: 0,
    nonPolarBSA: 0,
    totalPercent: parseNumber(row.ligand_bsa_pct),
    polarPercent: 0,
    nonPolarPercent: 0
  }))
}

export default {
  async getSystems() {
    const manifest = await getManifest()
    return [buildSystem(manifest)]
  },

  async getSystem() {
    const manifest = await getManifest()
    return buildSystem(manifest)
  },

  async renameSystem() { return { success: true } },

  async getInteractions(systemId) {
    const manifest = await getManifest()
    const frameRows = await getFrameRows()
    const totalFrames = getFrameNumbers(manifest).length

    return {
      system: systemId,
      totalFrames,
      interactions: buildInteractionAggregate(frameRows, totalFrames)
    }
  },

  async getAreaData(systemId) {
    const rows = await getSummaryRows()
    return {
      system: systemId,
      frames: buildAreaFrames(rows)
    }
  },

  async getTrends(systemId) {
    const rows = await getSummaryRows()
    const payload = buildTrendPayload(rows)
    return {
      system: systemId,
      trends: payload.trends,
      frameNumbers: payload.frameNumbers
    }
  },

  // Stubs for features not applicable to this static demo.
  async getAtomPairs() { return { pairs: [] } },
  async getAtomPairsBatch() { return { pairs: [] } },
  async getInteractionDistances() { return { pairs: [] } },
  async getConservedIslands() { return { islands: [] } },
  getFramePdbUrl() { return '' },
  async getFramePdbContent() { return '' },
  async getDistanceDistributions() { return { distributions: [] } },
  async uploadFile() { return { error: 'Upload not supported in static mode' } },
  async uploadFileWithOptions() { return { error: 'Upload not supported in static mode' } },
  async getStatus() { return { status: 'complete' } },
  async getJobs() { return [] }
}
