# %%

import json
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

import swifter

print(swifter.__version__)


# %%


def prepare_lists(path_lists):
    """
    Parse evaluation lists (i.e., probe and gallery lists)
    """
    path_gallery = path_lists.joinpath("gallery.json")
    path_probes = path_lists.joinpath("probes.json")
    path_gt = path_lists.joinpath("true_relatives.json")

    with open(path_gallery) as f:
        gallery = json.load(f)
    gallery.sort()
    gallery = [
        (i, g.split("/")[0], "/".join(g.split("/")[:2]), g)
        for i, g in enumerate(gallery)
    ]

    with open(path_probes) as f:
        probes = json.load(f)

    with open(path_gt) as f:
        groundtruth = json.load(f)
    fid_list = list(probes.keys())
    fid_list.sort()
    probes = [(fid, probes[fid], groundtruth[fid]) for fid in fid_list]

    return gallery, probes, fid_list


def load_gallery_features(path_in, gal):
    """
    Load features of gallery and return as dictionary FID.MID: <encoding>
    """
    mid_set = list(set([el[2] for el in gal]))
    mid_set.sort()

    return {
        mid: pd.read_pickle(path_in.joinpath(mid).joinpath("encodings.pkl"))
        for mid in tqdm(mid_set)
    }


def get_feature(fpath):
    if not Path(fpath).is_file():
        return None

    df = pd.read_pickle(fpath)
    keys = list(df.keys())
    ref = str(Path(keys[0]).parent)
    features_lut = {Path(k).name: v for k, v in df.items()}
    return ref, features_lut


def prepare_gallery(path_file, save_intermediate=False):
    # prepare gallery
    if path_file.is_file():
        gallery_features = pd.read_pickle(path_file)
        print(f"Loaded {path_file}")
    else:
        gallery_features = df_gallery.path.swifter.apply(get_feature)
        if save_intermediate:
            pd.to_pickle(gallery_features, path_file)
            print(f"Saved {path_file}")
    return gallery_features.values


# set paths
path_dir_root = Path("..").joinpath("data").joinpath("fiw-mm")
path_dir_features = path_dir_root.joinpath("FIDs-MM-features")
path_dir_fids = path_dir_root.joinpath("FIDs-MM")
path_dir_lists = path_dir_root.joinpath("lists")
path_dir_test = path_dir_lists.joinpath("test")

gallery_list, probe_lut, fids = prepare_lists(path_dir_test)

path_features_gallery = path_dir_test / "gallery-features.pkl"
path_feature_matrix_gallery = path_dir_test / "gallery-feature-matrix.pkl"
path_features_probe = path_dir_test / "probe-features.pkl"

mid_set = list(set([el[2] for el in gallery_list]))
mid_set.sort()

df_gallery = pd.DataFrame(mid_set, columns=["ref"])
df_gallery["path"] = str(path_dir_features) + "/" + df_gallery["ref"] + "/encodings.pkl"

df_probes = pd.DataFrame(probe_lut, columns=["fid", "ref", "relatives"])

df_gallery_features = prepare_gallery(path_features_gallery)

counter = 0
for features in df_gallery_features:
    # format gallery as feature matrix Nxd, where N-sample count; d-dims
    if features:
        counter += len(list(features[1].keys()))

if path_feature_matrix_gallery.is_file():
    print(f"Loading: {path_feature_matrix_gallery}")
    arr = pd.read_pickle(path_feature_matrix_gallery)
else:
    arr = np.empty((counter, 512))
    counter1 = 0
    for features in tqdm(df_gallery_features):
        # format gallery as feature matrix Nxd, where N-sample count; d-dims
        if features:
            for feature in features[1].values():
                nfeatures = len(feature)
                try:
                    arr[counter1 : (counter1 + nfeatures)] = feature
                    counter1 += nfeatures
                except Exception as e:
                    print(e.message)
                    pass
                finally:
                    arr[-nfeatures:] = feature
    pd.to_pickle(arr, path_feature_matrix_gallery)

for fid in tqdm(fids):
    # for each FID
    df_probe = df_probes.loc[df_probes.fid == fid]

    path_features = (path_dir_features / df_probe["ref"].values[0]).joinpath(
        "encodings.pkl"
    )
    if path_features.is_file():
        f = pd.read_pickle(path_features)
