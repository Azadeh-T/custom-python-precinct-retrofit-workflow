# LHS Runner — safer version matched to the user's current GhPython inputs
# Rhino 8 GhPython (CPython)
#
# Inputs expected on the GhPython component:
# RUN, RESET, N, Seed, Folder,
# UseSliders, SliderMode, GroupName, NamePrefix, VarNames, SliderGUIDs,
# CO2_total, y_CO2e_heat, y_CO2e_cool, y_CO2e_light,
# y_pet_neutral_1,
# heating_B1, cooling_B1, lighting_B1,
# heating_B2, cooling_B2, lighting_B2,
# heating_B3, cooling_B3, lighting_B3,
# face_outdoor_temp_B1, face_outdoor_temp_B2, face_outdoor_temp_B3,
# dry_bulb_temperature, relative_humidity, wind_speed,
# direct_normal_rad, direct_normal_ill,
# diffuse_horizontal_ill, diffuse_horizontal_rad,
# mrt_ave_hot, mrt_max_hot, short_dmrt, long_dmrt,
# pet_max, pet_ave, pet_min, pet_coldDD, pet_hotDD
#
# Outputs:
# sample_id, X_current, progress, log

import os
import csv
import json
import random
import hashlib
import scriptcontext as sc

import clr
clr.AddReference('System')
from System import Guid, Convert, Decimal as NetDecimal

clr.AddReference('Grasshopper')
import Grasshopper.Kernel as GHK
import Grasshopper.Kernel.Special as GHS

def schedule_next(ms=50):
    doc = gh_doc()
    def cb(d):
        ghenv.Component.ExpireSolution(False)
    doc.ScheduleSolution(ms, cb)
# ---------------------------
# Helpers
# ---------------------------
def gh_doc():
    return ghenv.Component.OnPingDocument()


def to_double(x):
    try:
        return float(x)
    except:
        try:
            return Convert.ToDouble(x)
        except:
            return float(str(x))


def to_decimal(x):
    try:
        return Convert.ToDecimal(x)
    except:
        return NetDecimal(str(x))


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def remove_if_exists(path):
    if os.path.isfile(path):
        os.remove(path)


def find_group_by_name(name):
    name = (name or "").strip()
    for obj in gh_doc().Objects:
        if isinstance(obj, GHK.GH_Group) and ((obj.NickName or "").strip() == name):
            return obj
    return None


def find_sliders_in_group(group):
    ids = set(group.ObjectIDs)
    sliders = []
    for obj in gh_doc().Objects:
        if obj.InstanceGuid in ids and isinstance(obj, GHS.GH_NumberSlider):
            sliders.append(obj)
    return sliders


def find_sliders_by_prefix(prefix):
    prefix = prefix or ""
    sliders = []
    for obj in gh_doc().Objects:
        if isinstance(obj, GHS.GH_NumberSlider):
            nm = (obj.NickName or "")
            if nm.startswith(prefix):
                sliders.append(obj)
    return sliders


def find_sliders_by_guids(guid_list):
    sliders = []
    wanted = [Guid(str(g)) for g in (guid_list or [])]
    for obj in gh_doc().Objects:
        if isinstance(obj, GHS.GH_NumberSlider) and obj.InstanceGuid in wanted:
            sliders.append(obj)
    return sliders


def slider_range(slider):
    lo = to_double(slider.Slider.Minimum)
    hi = to_double(slider.Slider.Maximum)
    step = None
    if hi > lo:
        try:
            ticks = slider.Slider.TickCount
            if ticks and ticks > 1:
                step = (hi - lo) / float(ticks - 1)
            else:
                step = (hi - lo) / 100.0
        except:
            step = (hi - lo) / 100.0
    return lo, hi, step


def quantize(x, lo, hi, step):
    x = max(lo, min(hi, float(x)))
    if step and step > 0:
        n = round((x - lo) / step)
        x = lo + n * step
    return x


def latin_hypercube(n_samples, n_vars, seed):
    rnd = random.Random(seed)
    mat = [[0.0] * n_vars for _ in range(n_samples)]
    for j in range(n_vars):
        bins = [(i + rnd.random()) / float(n_samples) for i in range(n_samples)]
        rnd.shuffle(bins)
        for i in range(n_samples):
            mat[i][j] = bins[i]
    return mat


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def append_csv_row(path, row):
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def read_csv_header(path):
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            return next(reader)
        except StopIteration:
            return None


def read_completed_sample_ids(results_csv, expected_header):
    if not os.path.isfile(results_csv) or os.path.getsize(results_csv) == 0:
        return []

    with open(results_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return []

        if header != expected_header:
            raise Exception(
                "results.csv header does not match the current script. "
                "Use RESET or a new Folder.\nExpected: {}\nFound: {}".format(expected_header, header)
            )

        ids = []
        for row_idx, row in enumerate(reader, start=2):
            if not row or all(str(c).strip() == "" for c in row):
                continue
            try:
                sid = int(row[0])
            except:
                raise Exception("Invalid sample_id at results.csv row {}.".format(row_idx))
            ids.append(sid)

    if ids:
        expected = list(range(1, len(ids) + 1))
        if ids != expected:
            raise Exception(
                "results.csv sample_id sequence is not contiguous from 1..k. "
                "Found: {}. Use RESET or repair the file.".format(ids)
            )

    return ids


def make_design_signature(names, guids, ranges, design, n_samples, seed, mode):
    payload = {
        "mode": mode,
        "N": int(n_samples),
        "seed": int(seed),
        "names": list(names),
        "guids": list(guids),
        "ranges": [[float(a), float(b), (None if c is None else float(c))] for (a, b, c) in ranges],
        "design": [[float(v) for v in row] for row in design]
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_meta(path, meta):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)


def load_meta(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set_slider_value(slider, value):
    dec_value = to_decimal(value)
    errors = []

    try:
        slider.Slider.Value = dec_value
        return
    except Exception as ex:
        errors.append("Slider.Value: {}".format(ex))

    try:
        slider.SetSliderValue(dec_value)
        return
    except Exception as ex:
        errors.append("SetSliderValue: {}".format(ex))

    raise Exception(
        "Failed to set slider '{}' (GUID {}). {}".format(
            slider.NickName, slider.InstanceGuid, " | ".join(errors)
        )
    )


def discover_sliders():
    if not UseSliders:
        raise Exception("UseSliders must be True. This script is slider-driven.")

    mode = (SliderMode or "GROUP").upper()

    if mode == "GROUP":
        group_name = GroupName or "SA_VARS"
        grp = find_group_by_name(group_name)
        if not grp:
            raise Exception("Group '{}' not found.".format(group_name))
        sliders = find_sliders_in_group(grp)

    elif mode == "PREFIX":
        sliders = find_sliders_by_prefix(NamePrefix or "SA_")

    elif mode == "GUID":
        sliders = find_sliders_by_guids(SliderGUIDs or [])

    else:
        raise Exception("SliderMode must be 'GROUP', 'PREFIX', or 'GUID'.")

    if len(sliders) == 0:
        raise Exception("No sliders found for mode '{}'.".format(mode))

    if VarNames and len(VarNames) == len(sliders):
        by_name = {(s.NickName or "").strip(): s for s in sliders}
        ordered = []
        for nm in VarNames:
            key = (nm or "").strip()
            if key not in by_name:
                raise Exception("VarNames contains '{}', but no matching slider was found.".format(nm))
            ordered.append(by_name[key])
        sliders = ordered
        names = list(VarNames)
    else:
        sliders.sort(key=lambda s: (s.Attributes.Pivot.X, s.Attributes.Pivot.Y))
        names = [(s.NickName or "var{}".format(i + 1)).strip() for i, s in enumerate(sliders)]

    ranges = [slider_range(s) for s in sliders]
    guids = [str(s.InstanceGuid) for s in sliders]

    return mode, sliders, names, ranges, guids


# ---------------------------
# Sticky state
# ---------------------------
KEY = "LHS_RUNNER_EXACT_INPUTS_V1"


def get_state(reset=False):
    if reset and KEY in sc.sticky:
        sc.sticky.pop(KEY, None)

    if KEY not in sc.sticky:
        sc.sticky[KEY] = {
            "init": False,
            "i": 0,
            "phase": "set",
            "names": [],
            "sliders": [],
            "ranges": [],
            "design": [],
            "headers": [],
            "paths": {},
            "meta": {}
        }
    return sc.sticky[KEY]


# ---------------------------
# Main
# ---------------------------
sample_id, X_current, progress, log = 0, [], 0.0, ""

OUTPUT_SPECS = [
    ("CO2e_total", "CO2e_total"),
    ("CO2e_heat", "y_CO2e_heat"),
    ("CO2e_cool", "y_CO2e_cool"),
    ("CO2e_light", "y_CO2e_light"),
    ("pet_neutral_1", "y_pet_neutral_1"),

    ("heating_B1", "heating_B1"),
    ("cooling_B1", "cooling_B1"),
    ("lighting_B1", "lighting_B1"),

    ("heating_B2", "heating_B2"),
    ("cooling_B2", "cooling_B2"),
    ("lighting_B2", "lighting_B2"),

    ("heating_B3", "heating_B3"),
    ("cooling_B3", "cooling_B3"),
    ("lighting_B3", "lighting_B3"),

    ("face_outdoor_temp_B1", "face_outdoor_temp_B1"),
    ("face_outdoor_temp_B2", "face_outdoor_temp_B2"),
    ("face_outdoor_temp_B3", "face_outdoor_temp_B3"),

    ("dry_bulb_temperature", "dry_bulb_temperature"),
    ("relative_humidity", "relative_humidity"),
    ("wind_speed", "wind_speed"),

    ("direct_normal_rad", "direct_normal_rad"),
    ("direct_normal_ill", "direct_normal_ill"),
    ("diffuse_horizontal_ill", "diffuse_horizontal_ill"),
    ("diffuse_horizontal_rad", "diffuse_horizontal_rad"),

    ("mrt_ave_hot", "mrt_ave_hot"),
    ("mrt_max_hot", "mrt_max_hot"),
    ("short_dmrt", "short_dmrt"),
    ("long_dmrt", "long_dmrt"),

    ("pet_max_h", "pet_max_h"),
    ("pet_ave_h", "pet_ave_h"),
    ("pet_min_h", "pet_min_h"),
    ("pet_coldDD", "pet_coldDD"),
    ("pet_hotDD", "pet_hotDD"),
    ("percent_discom_hot", "percent_discom_hot"),
    ("percent_dis_c", "percent_dis_c"),
]

RESULT_HEADERS = ["sample_id"] + [header for header, _ in OUTPUT_SPECS]

try:
    folder = Folder or os.path.join(os.path.expanduser("~"), "SA_runs")
    design_csv = os.path.join(folder, "design.csv")
    results_csv = os.path.join(folder, "results.csv")
    meta_json = os.path.join(folder, "run_meta.json")

    if RESET:
        ensure_dir(folder)
        get_state(reset=True)
        remove_if_exists(design_csv)
        remove_if_exists(results_csv)
        remove_if_exists(meta_json)
        log = "Reset done. Deleted design.csv, results.csv, and run_meta.json in '{}'.".format(folder)

    st = get_state()

    if RUN:
        if not st["init"]:
            n_samples = int(N)
            if n_samples <= 0:
                raise Exception("N must be a positive integer.")

            if Seed is None:
                raise Exception("Seed must be provided as an integer for reproducible runs/resume.")

            seed_val = int(Seed)

            mode, sliders, names, ranges, guids = discover_sliders()
            n_vars = len(sliders)

            u = latin_hypercube(n_samples, n_vars, seed_val)
            design = []
            for row in u:
                vals = []
                for j, uu in enumerate(row):
                    lo, hi, step = ranges[j]
                    raw = lo + uu * (hi - lo)
                    vals.append(quantize(raw, lo, hi, step))
                design.append(vals)

            design_signature = make_design_signature(
                names=names,
                guids=guids,
                ranges=ranges,
                design=design,
                n_samples=n_samples,
                seed=seed_val,
                mode=mode
            )

            current_meta = {
                "mode": mode,
                "N": n_samples,
                "seed": seed_val,
                "names": names,
                "guids": guids,
                "ranges": [[float(a), float(b), (None if c is None else float(c))] for (a, b, c) in ranges],
                "design_signature": design_signature,
                "result_headers": RESULT_HEADERS
            }

            ensure_dir(folder)
            existing_files = [p for p in [design_csv, results_csv, meta_json] if os.path.isfile(p)]

            if existing_files:
                saved_meta = load_meta(meta_json)
                if saved_meta is None:
                    raise Exception(
                        "Existing run files were found but run_meta.json is missing. "
                        "Use RESET or choose a new Folder."
                    )

                comparable_saved = {
                    "mode": saved_meta.get("mode"),
                    "N": saved_meta.get("N"),
                    "seed": saved_meta.get("seed"),
                    "names": saved_meta.get("names"),
                    "guids": saved_meta.get("guids"),
                    "ranges": saved_meta.get("ranges"),
                    "design_signature": saved_meta.get("design_signature"),
                    "result_headers": saved_meta.get("result_headers")
                }

                if comparable_saved != current_meta:
                    raise Exception(
                        "The existing run in this Folder does not match the current slider setup/design/output header. "
                        "Use RESET or choose a new Folder."
                    )

                design_header = read_csv_header(design_csv)
                expected_design_header = ["sample_id"] + names
                if design_header != expected_design_header:
                    raise Exception(
                        "design.csv header does not match the current script/setup. "
                        "Use RESET or choose a new Folder."
                    )

                completed_ids = read_completed_sample_ids(results_csv, RESULT_HEADERS)
                completed = len(completed_ids)

            else:
                design_rows = []
                for sid, row in enumerate(design, start=1):
                    design_rows.append([sid] + row)
                write_csv(design_csv, ["sample_id"] + names, design_rows)
                write_csv(results_csv, RESULT_HEADERS, [])
                save_meta(meta_json, current_meta)
                completed = 0

            st.update({
                "init": True,
                "i": completed,
                "phase": "set",
                "names": names,
                "sliders": sliders,
                "ranges": ranges,
                "design": design,
                "headers": RESULT_HEADERS,
                "paths": {"design": design_csv, "results": results_csv, "meta": meta_json},
                "meta": current_meta
            })

            if completed > 0:
                log = "Init OK (resume): k={}, N={}, starting from sample {}.".format(
                    n_vars, n_samples, completed + 1
                )
            else:
                log = "Init OK (fresh): k={}, N={}, folder='{}'.".format(n_vars, n_samples, folder)

        i = st["i"]
        n_total = len(st["design"])

        if i >= n_total:
            sample_id = n_total
            X_current = []
            progress = 1.0
            log = "All samples complete -> {}".format(st["paths"]["results"])

        else:
            sample_id = i + 1
            X_current = st["design"][i]
            progress = float(i) / float(n_total)

            if st["phase"] == "set":
                for slider, val, (lo, hi, step) in zip(st["sliders"], X_current, st["ranges"]):
                    vv = quantize(val, lo, hi, step)
                    set_slider_value(slider, vv)

                st["phase"] = "read"
                log = "Set inputs for sample {}/{}. Next solve will read outputs.".format(sample_id, n_total)
                schedule_next(50)

            elif st["phase"] == "read":
                ys_raw = [globals().get(var_name, None) for _, var_name in OUTPUT_SPECS]
                missing = [header for (header, _), v in zip(OUTPUT_SPECS, ys_raw) if v is None]

                if missing:
                    preview = ", ".join(missing[:5])
                    if len(missing) > 5:
                        preview += ", ..."
                    log = "Waiting for outputs for sample {}. Missing {} field(s): {}".format(
                        sample_id, len(missing), preview
                    )
                else:
                    ys = [to_double(v) for v in ys_raw]
                    append_csv_row(st["paths"]["results"], [sample_id] + ys)
                    st["i"] = i + 1
                    st["phase"] = "set"
                    log = "Logged sample {} successfully.".format(sample_id)
                    schedule_next(50)

    else:
        st = get_state()
        i = st["i"]
        n_total = len(st["design"]) if st["design"] else max(1, int(N or 1))
        sample_id = min(i + 1, n_total)
        X_current = st["design"][i] if (st["design"] and i < len(st["design"])) else []
        progress = float(i) / float(n_total)
        log = "Paused."

except Exception as e:
    log = "ERROR: {}".format(e)
