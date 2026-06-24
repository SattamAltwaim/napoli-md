"""Data access and aggregation for frame-split NAPOLI CSV output."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SYSTEM_ID = "simulated-trajectory-8cgk-6uq"
FINAL_FILE_SUFFIX = "_final_file.csv"

TREND_LABELS = {
    "pi_pi": "\u03c0-\u03c0 interactions",
    "amino_pi": "Amino-\u03c0 interactions",
    "anion_pi": "Anion-\u03c0 interactions",
    "apolar_vdw": "Apolar vdW contacts",
    "ch_on": "CH-O/N bonds",
    "ch_pi": "CH-\u03c0 interactions",
    "cation_pi": "Cation-\u03c0 interactions",
    "clash": "Clashes",
    "h_bond": "H-bonds",
    "halogen": "Halogen bonds",
    "lone_pair_pi": "Lone pair-\u03c0 interactions",
    "metal": "Metal mediated",
    "ons_oh_pi": "O/N/SH-\u03c0 interactions",
    "polar_vdw": "Polar vdW contacts",
    "proximal": "Proximal contacts",
    "salt_bridge": "Salt-bridges",
    "ss_bond": "S-S bonds",
    "water": "Water mediated",
}

TYPE_ORDER = [
    "H-bond",
    "CH-O/N bond",
    "Polar vdW contact",
    "CH-\u03c0 Interaction",
    "Proximal contact",
]

DETAIL_FILE_TYPES = [
    ("_H-bond-alt.csv", None),
    ("_H-bond.csv", "H-bond"),
    ("_C-H_ON.csv", "CH-O/N bond"),
    ("_Polar_vdw.csv", "Polar vdW contact"),
    ("_C-H_pi.csv", "CH-\u03c0 Interaction"),
    ("_Proximal.csv", "Proximal contact"),
    ("_pi-pi.csv", "\u03c0-\u03c0 Interaction"),
    ("_Anion_pi.csv", "Anion-\u03c0 Interaction"),
    ("_Apolar_vdw.csv", "Apolar vdW contact"),
    ("_Cation_pi.csv", "Cation-\u03c0 Interaction"),
    ("_Clash.csv", "Clash"),
    ("_Halogen_bond.csv", "Halogen bond"),
    ("_Halogen_pi.csv", "Halogen-\u03c0 Interaction"),
    ("_Lone_pair_pi.csv", "Lone pair-\u03c0 Interaction"),
    ("_Metal_Mediated.csv", "Metal mediated"),
    ("_N-S-O-H_pi.csv", "O/N/SH-\u03c0 Interaction"),
    ("_Salt_bridge.csv", "Salt-bridge"),
    ("_Water_Mediated.csv", "Water mediated"),
]

AREA_LIGAND_PROPERTIES = {
    "Bound-Ligand Accessible Surface Area (ASA) (Å²)": "boundLigandASA",
    "Unbound-Ligand Accessible Surface Area (ASA) (Å²)": "unboundLigandASA",
    "Ligand Buried Surface Area (BSA) (Å²)": "ligandBSA",
    "Ligand Buried Surface Area (BSA) (%)": "ligandBSAPercent",
}

AREA_SERIES = [
    {
        "key": "boundLigandASA",
        "label": "Bound-Ligand ASA",
        "unit": "Å²",
        "kind": "absolute",
        "color": "#3B6EF5",
        "dashStyle": "Solid",
        "symbol": "circle",
    },
    {
        "key": "unboundLigandASA",
        "label": "Unbound-Ligand ASA",
        "unit": "Å²",
        "kind": "absolute",
        "color": "#5856D6",
        "dashStyle": "ShortDash",
        "symbol": "diamond",
    },
    {
        "key": "ligandBSA",
        "label": "Ligand BSA",
        "unit": "Å²",
        "kind": "absolute",
        "color": "#FF9500",
        "dashStyle": "Solid",
        "symbol": "triangle",
        "percentKey": "ligandBSAPercent",
    },
    {
        "key": "proteinBoundASA",
        "label": "NA/Protein Bound ASA",
        "unit": "Å²",
        "kind": "absolute",
        "color": "#34C759",
        "dashStyle": "Dash",
        "symbol": "square",
    },
    {
        "key": "proteinUnboundASA",
        "label": "NA/Protein Unbound ASA",
        "unit": "Å²",
        "kind": "absolute",
        "color": "#30B0C7",
        "dashStyle": "ShortDot",
        "symbol": "circle",
    },
    {
        "key": "proteinBSA",
        "label": "NA/Protein Residue BSA",
        "unit": "Å²",
        "kind": "absolute",
        "color": "#FF3B30",
        "dashStyle": "Dot",
        "symbol": "square",
        "percentKey": "proteinBSAPercent",
    },
    {
        "key": "ligandBSAPercent",
        "label": "Ligand BSA",
        "unit": "%",
        "kind": "percent",
        "color": "#FF9500",
        "dashStyle": "Solid",
        "symbol": "triangle",
    },
    {
        "key": "proteinBSAPercent",
        "label": "NA/Protein Residue BSA",
        "unit": "%",
        "kind": "percent",
        "color": "#FF3B30",
        "dashStyle": "Dot",
        "symbol": "square",
    },
]

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


class DataNotFoundError(RuntimeError):
    pass


class UnknownSystemError(RuntimeError):
    pass


def parse_number(value, fallback=0.0):
    if value is None:
        return fallback

    match = NUMBER_RE.search(str(value))
    if not match:
        return fallback

    try:
        return float(match.group(0))
    except ValueError:
        return fallback


def parse_int(value, fallback=0):
    parsed = parse_number(value, fallback=None)
    if parsed is None:
        return fallback
    return int(parsed)


def read_csv(path: Path):
    if not path.exists():
        raise DataNotFoundError(f"Missing CSV: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def format_residue_id(res_name, res_num, chain):
    if not res_name or not res_num or not chain:
        return ""
    return f"{str(res_name).strip()}{parse_int(res_num)}_{str(chain).strip()}"


def normalize_interaction_type(raw_type):
    cleaned = re.sub(r"\s+", " ", str(raw_type or "").replace("*", "")).strip()
    if not cleaned:
        return ""

    lower = cleaned.lower()
    if lower == "h-bond":
        return "H-bond"
    if lower == "ch-o/n bond":
        return "CH-O/N bond"
    if lower == "polar vdw contact":
        return "Polar vdW contact"
    if re.match(r"^ch-\s*\u03c0 interaction$", cleaned, re.IGNORECASE):
        return "CH-\u03c0 Interaction"
    if lower == "proximal contact":
        return "Proximal contact"
    return cleaned


def split_interaction_types(types_string):
    return [
        normalized
        for normalized in (normalize_interaction_type(part) for part in str(types_string or "").split(";"))
        if normalized
    ]


def sort_types(types):
    def sort_key(type_name):
        try:
            return (0, TYPE_ORDER.index(type_name), type_name)
        except ValueError:
            return (1, len(TYPE_ORDER), type_name)

    return sorted(types, key=sort_key)


def frame_number_from_dir(path: Path):
    match = re.search(r"(\d+)$", path.name)
    return int(match.group(1)) if match else 0


def first_existing_value(row, keys):
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return ""


def distance_from_row(row):
    distance_keys = [key for key in row.keys() if key and "Distance" in key]
    distances = [parse_number(row.get(key), fallback=None) for key in distance_keys]
    distances = [distance for distance in distances if distance is not None]
    if not distances:
        return None
    return sum(distances) / len(distances)


def read_ligand_area_file(path: Path):
    values = {}
    for row in read_csv(path):
        key = AREA_LIGAND_PROPERTIES.get(str(row.get("Property", "")).strip())
        if key:
            values[key] = parse_number(row.get("Value"))
    return values


def read_residue_area_file(path: Path):
    totals = defaultdict(float)
    count = 0

    for row in read_csv(path):
        count += 1
        totals["proteinBoundASA"] += parse_number(row.get("ASA of NA/Protein Res - BOUND (Å²)"))
        totals["proteinUnboundASA"] += parse_number(row.get("ASA of NA/Protein Res - UNBOUND (Å²)"))
        totals["proteinBSA"] += parse_number(row.get("BSA of NA/Protein Res (Å²)"))

    if totals["proteinUnboundASA"]:
        totals["proteinBSAPercent"] = (totals["proteinBSA"] / totals["proteinUnboundASA"]) * 100

    return {**totals, "residueCount": count}


def available_area_series(frames):
    return [
        series
        for series in AREA_SERIES
        if any(frame.get(series["key"]) is not None for frame in frames)
    ]


def detail_type_for_file(path: Path):
    name = path.name
    for suffix, interaction_type in DETAIL_FILE_TYPES:
        if name.endswith(suffix):
            return interaction_type
    return None


def atom_pair_from_row(row):
    left = first_existing_value(
        row,
        [
            "NA/Protein Atom",
            "C Atom",
            "Anion Atom",
            "Cation Atom",
            "Halogen Atom",
            "Lone_pair Atom",
            "N/S/O Atom",
            "Metal Identity",
            "Water Identity",
        ],
    )
    right = first_existing_value(
        row,
        [
            "Ligand Atom",
            "Ring From",
            "Ligand Ring Num",
            "Water Identity",
            "Metal Identity",
        ],
    )

    if left and right:
        return f"{left} - {right}"
    return left or right or "Atom pair"


def row_matches_pair(row, params):
    checks = [
        ("NA/Protein Res Name", "resName1"),
        ("NA/Protein Chain", "chain1"),
        ("Ligand Res Name", "resName2"),
        ("Ligand Chain", "chain2"),
    ]
    for row_key, param_key in checks:
        expected = params.get(param_key)
        if expected is not None and str(row.get(row_key, "")).strip() != str(expected).strip():
            return False

    numeric_checks = [
        ("NA/Protein Res Number", "resNum1"),
        ("Ligand Res Number", "resNum2"),
    ]
    for row_key, param_key in numeric_checks:
        expected = params.get(param_key)
        if expected is not None and parse_int(row.get(row_key)) != parse_int(expected):
            return False

    return True


class TrajectoryDataset:
    def __init__(self, data_root: Path):
        self.data_root = Path(data_root).resolve()
        self._manifest = None
        self._summary_rows = None
        self._frame_dirs = None
        self._frame_final_rows = None
        self._detail_rows = None

    def validate_system(self, system_id):
        return None

    @property
    def manifest_path(self):
        return self.data_root / "simulation_manifest.json"

    @property
    def summary_path(self):
        return self.data_root / "trajectory_summary.csv"

    def manifest(self):
        if self._manifest is None:
            if not self.manifest_path.exists():
                raise DataNotFoundError(f"Missing manifest: {self.manifest_path}")
            self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return self._manifest

    def summary_rows(self):
        if self._summary_rows is None:
            self._summary_rows = read_csv(self.summary_path)
        return self._summary_rows

    def frame_dirs(self):
        if self._frame_dirs is None:
            if not self.data_root.exists():
                raise DataNotFoundError(f"Missing data directory: {self.data_root}")
            self._frame_dirs = sorted(
                [path for path in self.data_root.iterdir() if path.is_dir() and path.name.startswith("frame_")],
                key=frame_number_from_dir,
            )
        return self._frame_dirs

    def frame_numbers(self):
        manifest_frames = [
            parse_int(frame.get("frame"))
            for frame in self.manifest().get("frame_summaries", [])
            if parse_int(frame.get("frame")) > 0
        ]
        if manifest_frames:
            return manifest_frames
        return [frame_number_from_dir(path) for path in self.frame_dirs()]

    def ligand_code(self):
        return str(self.manifest().get("source", {}).get("ligand", "6UQ")).split("-")[0]

    def interacting_chains(self):
        raw = str(self.manifest().get("source", {}).get("interacting_chains", "a l"))
        chains = [chain for chain in raw.split() if chain]
        return chains or ["a", "l"]

    def system(self, system_id=None):
        system_id = system_id or self.data_root.name or SYSTEM_ID
        source = self.manifest().get("source", {})
        pdb = str(source.get("pdb", "8CGK")).upper()
        ligand = self.ligand_code()
        chains = self.interacting_chains()
        date_created = datetime.fromtimestamp(self.data_root.stat().st_mtime, timezone.utc).isoformat()

        return {
            "id": system_id,
            "name": f"{pdb} / {ligand} Simulated Trajectory",
            "frames": len(self.frame_numbers()),
            "chain1": "/".join(chains),
            "chain2": ligand,
            "jobId": system_id,
            "dateCreated": date_created,
            "status": "ready",
            "isExample": False,
        }

    def final_rows_by_frame(self):
        if self._frame_final_rows is None:
            frame_rows = []
            for frame_dir in self.frame_dirs():
                final_files = sorted(frame_dir.glob(f"*{FINAL_FILE_SUFFIX}"))
                if not final_files:
                    continue
                frame_rows.append(
                    {
                        "frame": frame_number_from_dir(frame_dir),
                        "rows": read_csv(final_files[0]),
                    }
                )
            self._frame_final_rows = frame_rows
        return self._frame_final_rows

    def interactions(self, system_id):
        self.validate_system(system_id)
        total_frames = len(self.frame_numbers())
        interaction_map = {}

        for frame_data in self.final_rows_by_frame():
            frame = frame_data["frame"]
            for row in frame_data["rows"]:
                types = set(split_interaction_types(row.get("Type of Interactions")))
                if not types:
                    continue

                res_name1 = row.get("NA/Protein Res Name")
                res_num1 = row.get("NA/Protein Res Number")
                chain1 = row.get("NA/Protein Chain")
                res_name2 = row.get("Ligand Res Name")
                res_num2 = row.get("Ligand Res Number")
                chain2 = row.get("Ligand Chain")
                id1 = format_residue_id(res_name1, res_num1, chain1)
                id2 = format_residue_id(res_name2, res_num2, chain2)
                if not id1 or not id2:
                    continue

                key = f"{id1}__{id2}"
                if key not in interaction_map:
                    interaction_map[key] = {
                        "resName1": res_name1,
                        "resNum1": parse_int(res_num1),
                        "chain1": chain1,
                        "id1": id1,
                        "resName2": res_name2,
                        "resNum2": parse_int(res_num2),
                        "chain2": chain2,
                        "id2": id2,
                        "frames": set(),
                        "types": set(),
                        "typeFrames": defaultdict(set),
                    }

                entry = interaction_map[key]
                entry["frames"].add(frame)
                for interaction_type in types:
                    entry["types"].add(interaction_type)
                    entry["typeFrames"][interaction_type].add(frame)

        interactions = []
        for entry in interaction_map.values():
            frames = sorted(entry["frames"])
            types = sort_types(entry["types"])
            type_frames = {
                interaction_type: sorted(entry["typeFrames"][interaction_type])
                for interaction_type in types
            }
            type_persistence = {
                interaction_type: len(frames_for_type) / total_frames if total_frames else 0
                for interaction_type, frames_for_type in type_frames.items()
            }

            interactions.append(
                {
                    "resName1": entry["resName1"],
                    "resNum1": entry["resNum1"],
                    "chain1": entry["chain1"],
                    "id1": entry["id1"],
                    "resName2": entry["resName2"],
                    "resNum2": entry["resNum2"],
                    "chain2": entry["chain2"],
                    "id2": entry["id2"],
                    "frameCount": len(frames),
                    "consistency": len(frames) / total_frames if total_frames else 0,
                    "types": "; ".join(types),
                    "typesArray": types,
                    "typePersistence": type_persistence,
                    "frames": frames,
                    "typeFrames": type_frames,
                }
            )

        interactions.sort(key=lambda item: (-item["consistency"], item["resNum1"], item["id1"]))
        return {"system": system_id, "totalFrames": total_frames, "interactions": interactions}

    def area(self, system_id):
        self.validate_system(system_id)
        frames = []

        for frame_dir in self.frame_dirs():
            frame = frame_number_from_dir(frame_dir)
            frame_data = {"frame": frame}

            for path in sorted(frame_dir.glob("*asa_stats_ligand.csv")):
                frame_data.update(read_ligand_area_file(path))

            for path in sorted(frame_dir.glob("*asa_stats_per_res.csv")):
                frame_data.update(read_residue_area_file(path))

            if len(frame_data) > 1:
                frame_data["totalBSA"] = frame_data.get("ligandBSA")
                frame_data["totalPercent"] = frame_data.get("ligandBSAPercent")
                frames.append(frame_data)

        if not frames:
            for row in self.summary_rows():
                frames.append(
                    {
                        "frame": parse_int(row.get("frame")),
                        "ligandBSA": parse_number(row.get("ligand_bsa_a2")),
                        "ligandBSAPercent": parse_number(row.get("ligand_bsa_pct")),
                        "totalBSA": parse_number(row.get("ligand_bsa_a2")),
                        "totalPercent": parse_number(row.get("ligand_bsa_pct")),
                    }
                )

        frames.sort(key=lambda item: item["frame"])
        return {"system": system_id, "frames": frames, "series": available_area_series(frames)}

    def trends(self, system_id):
        self.validate_system(system_id)
        rows = self.summary_rows()
        frame_numbers = [parse_int(row.get("frame")) for row in rows]
        zeroes = [0 for _ in rows]
        trends = {label: list(zeroes) for label in TREND_LABELS.values()}

        trends[TREND_LABELS["h_bond"]] = [
            parse_int(row.get("h_bond")) + parse_int(row.get("h_bond_star")) for row in rows
        ]
        trends[TREND_LABELS["ch_on"]] = [
            parse_int(row.get("ch_o_n")) + parse_int(row.get("ch_o_n_star")) for row in rows
        ]
        trends[TREND_LABELS["polar_vdw"]] = [
            parse_int(row.get("polar_vdw")) + parse_int(row.get("polar_vdw_star")) for row in rows
        ]
        trends[TREND_LABELS["ch_pi"]] = [parse_int(row.get("ch_pi")) for row in rows]
        trends[TREND_LABELS["proximal"]] = [parse_int(row.get("proximal_only")) for row in rows]

        return {"system": system_id, "trends": trends, "frameNumbers": frame_numbers}

    def detail_rows(self):
        if self._detail_rows is None:
            rows = []
            for frame_dir in self.frame_dirs():
                frame = frame_number_from_dir(frame_dir)
                for path in sorted(frame_dir.glob("*.csv")):
                    interaction_type = detail_type_for_file(path)
                    if not interaction_type:
                        continue
                    for row in read_csv(path):
                        rows.append({"frame": frame, "type": interaction_type, "row": row})
            self._detail_rows = rows
        return self._detail_rows

    def atom_pairs(self, system_id, params):
        self.validate_system(system_id)
        total_frames = len(self.frame_numbers())
        atom_pairs = {}
        by_frame = defaultdict(list)

        for item in self.detail_rows():
            row = item["row"]
            if not row_matches_pair(row, params):
                continue

            frame = item["frame"]
            interaction_type = item["type"]
            atom_pair = atom_pair_from_row(row)
            distance = distance_from_row(row)
            key = f"{atom_pair}__{interaction_type}"

            if key not in atom_pairs:
                atom_pairs[key] = {
                    "atomPair": atom_pair,
                    "interactionType": interaction_type,
                    "frames": set(),
                    "distances": [],
                }

            atom_pairs[key]["frames"].add(frame)
            if distance is not None:
                atom_pairs[key]["distances"].append(distance)

            by_frame[str(frame)].append(
                {
                    "frame": frame,
                    "atomPair": atom_pair,
                    "interactionType": interaction_type,
                    "distance": distance,
                }
            )

        atom_pair_list = []
        for entry in atom_pairs.values():
            frames = sorted(entry["frames"])
            distances = entry["distances"]
            atom_pair_list.append(
                {
                    "atomPair": entry["atomPair"],
                    "interactionType": entry["interactionType"],
                    "frames": frames,
                    "frameCount": len(frames),
                    "consistency": len(frames) / total_frames if total_frames else 0,
                    "avgDistance": sum(distances) / len(distances) if distances else None,
                }
            )

        atom_pair_list.sort(key=lambda item: (-item["frameCount"], item["atomPair"]))
        pair_label = (
            f"{params.get('chain1')}-{params.get('resName1')}{params.get('resNum1')}_"
            f"{params.get('chain2')}-{params.get('resName2')}{params.get('resNum2')}"
        )

        return {
            "system": system_id,
            "pair": pair_label,
            "totalFrames": total_frames,
            "atomPairs": atom_pair_list,
            "atomPairsByFrame": dict(by_frame),
            "transitions": [],
        }

    def atom_pairs_batch(self, system_id, pairs):
        self.validate_system(system_id)
        result = {}
        for params in pairs:
            key = (
                f"{params.get('chain1')}-{params.get('resName1')}{params.get('resNum1')}_"
                f"{params.get('chain2')}-{params.get('resName2')}{params.get('resNum2')}"
            )
            result[key] = self.atom_pairs(system_id, params)
        return result

    def interaction_distances(self, system_id):
        self.validate_system(system_id)
        distances = defaultdict(lambda: defaultdict(dict))

        for item in self.detail_rows():
            row = item["row"]
            id1 = format_residue_id(
                row.get("NA/Protein Res Name"),
                row.get("NA/Protein Res Number"),
                row.get("NA/Protein Chain"),
            )
            id2 = format_residue_id(
                row.get("Ligand Res Name"),
                row.get("Ligand Res Number"),
                row.get("Ligand Chain"),
            )
            distance = distance_from_row(row)
            if not id1 or not id2 or distance is None:
                continue

            pair_key = f"{id1}__{id2}"
            frame_key = str(item["frame"])
            interaction_type = item["type"]
            existing = distances[pair_key][frame_key].get(interaction_type)
            if existing is None:
                distances[pair_key][frame_key][interaction_type] = distance
            else:
                distances[pair_key][frame_key][interaction_type] = (existing + distance) / 2

        return {
            "system": system_id,
            "distances": {pair: dict(frames) for pair, frames in distances.items()},
        }

    def distance_distributions(self, system_id, interaction_types):
        self.validate_system(system_id)
        total_frames = len(self.frame_numbers())
        selected = set(interaction_types or [])
        pairs = {}

        for item in self.detail_rows():
            interaction_type = item["type"]
            if selected and interaction_type not in selected:
                continue

            row = item["row"]
            id1 = format_residue_id(
                row.get("NA/Protein Res Name"),
                row.get("NA/Protein Res Number"),
                row.get("NA/Protein Chain"),
            )
            id2 = format_residue_id(
                row.get("Ligand Res Name"),
                row.get("Ligand Res Number"),
                row.get("Ligand Chain"),
            )
            distance = distance_from_row(row)
            if not id1 or not id2 or distance is None:
                continue

            pair_key = f"{id1}__{id2}__{interaction_type}"
            if pair_key not in pairs:
                pairs[pair_key] = {
                    "resName1": row.get("NA/Protein Res Name"),
                    "resNum1": parse_int(row.get("NA/Protein Res Number")),
                    "chain1": row.get("NA/Protein Chain"),
                    "resName2": row.get("Ligand Res Name"),
                    "resNum2": parse_int(row.get("Ligand Res Number")),
                    "chain2": row.get("Ligand Chain"),
                    "interactionType": interaction_type,
                    "distances": [],
                    "frames": set(),
                }

            pairs[pair_key]["distances"].append(distance)
            pairs[pair_key]["frames"].add(item["frame"])

        result = []
        for entry in pairs.values():
            frame_count = len(entry["frames"])
            result.append(
                {
                    "resName1": entry["resName1"],
                    "resNum1": entry["resNum1"],
                    "chain1": entry["chain1"],
                    "resName2": entry["resName2"],
                    "resNum2": entry["resNum2"],
                    "chain2": entry["chain2"],
                    "interactionType": entry["interactionType"],
                    "distances": entry["distances"],
                    "frameCount": frame_count,
                    "totalMeasurements": len(entry["distances"]),
                    "consistency": frame_count / total_frames if total_frames else 0,
                }
            )

        result.sort(key=lambda item: (-item["consistency"], -item["totalMeasurements"]))
        return {"system": system_id, "pairs": result}


class TrajectoryRepository:
    """Discovers system/job folders and delegates aggregation to per-job readers."""

    def __init__(self, systems_root: Path):
        self.systems_root = Path(systems_root).resolve()
        self._datasets = {}

    @property
    def data_root(self):
        return self.systems_root

    def _is_system_dir(self, path: Path):
        if not path.is_dir():
            return False
        return any(child.is_dir() and child.name.startswith("frame_") for child in path.iterdir())

    def system_dirs(self):
        if not self.systems_root.exists():
            raise DataNotFoundError(f"Missing systems directory: {self.systems_root}")

        if self._is_system_dir(self.systems_root):
            return [self.systems_root]

        return [
            path
            for path in sorted(self.systems_root.iterdir(), key=lambda item: item.name.lower())
            if not path.name.startswith(".") and self._is_system_dir(path)
        ]

    def system_dir(self, system_id):
        for path in self.system_dirs():
            if path.name == system_id:
                return path

        dirs = self.system_dirs()
        if system_id == SYSTEM_ID and len(dirs) == 1:
            return dirs[0]

        raise UnknownSystemError(f"Unknown system: {system_id}")

    def dataset(self, system_id):
        path = self.system_dir(system_id)
        cache_key = str(path)
        if cache_key not in self._datasets:
            self._datasets[cache_key] = TrajectoryDataset(path)
        return self._datasets[cache_key]

    def validate_system(self, system_id):
        self.system_dir(system_id)

    def systems(self):
        systems = []
        for path in self.system_dirs():
            try:
                systems.append(self.dataset(path.name).system(path.name))
            except DataNotFoundError:
                continue
        return systems

    def system(self, system_id):
        return self.dataset(system_id).system(self.system_dir(system_id).name)

    def jobs(self):
        return [
            {
                "job_id": system["jobId"],
                "pdb_name": system["name"],
                "system_id": system["id"],
                "analysis_job_id": system["jobId"],
                "status": "completed",
                "created_at": system.get("dateCreated"),
                "frames": system.get("frames", 0),
                "progress": 100,
                "step_label": "complete",
            }
            for system in self.systems()
        ]

    def interactions(self, system_id):
        return self.dataset(system_id).interactions(self.system_dir(system_id).name)

    def area(self, system_id):
        return self.dataset(system_id).area(self.system_dir(system_id).name)

    def trends(self, system_id):
        return self.dataset(system_id).trends(self.system_dir(system_id).name)

    def atom_pairs(self, system_id, params):
        return self.dataset(system_id).atom_pairs(self.system_dir(system_id).name, params)

    def atom_pairs_batch(self, system_id, pairs):
        return self.dataset(system_id).atom_pairs_batch(self.system_dir(system_id).name, pairs)

    def interaction_distances(self, system_id):
        return self.dataset(system_id).interaction_distances(self.system_dir(system_id).name)

    def distance_distributions(self, system_id, interaction_types):
        return self.dataset(system_id).distance_distributions(self.system_dir(system_id).name, interaction_types)
