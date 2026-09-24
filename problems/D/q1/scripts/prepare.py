"""Rebuild geometry from the original XLSX/TIF/MAT, no result dependencies."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT, load_inputs, provenance, write_json, write_csv
from model.geometry import load_dem, geometry, check_geometry


def prepare(out, raw=None, method=None):
    config = json.loads((ROOT/'data/model_config.json').read_text(encoding='utf-8'))
    method = method or config['distance_method']
    nodes, aircraft, boxes = load_inputs(raw)
    dem = load_dem(raw)
    geo,cells = geometry(nodes,dem,method)
    audit = check_geometry(nodes,dem,geo,cells)
    write_json(out/'input_manifest.json',dict(raw_files=provenance(raw), distance_method=method,
               boxes=len(boxes), nodes=len(nodes), aircraft_types=len(aircraft)))
    write_json(out/'geometry.json',geo)
    write_csv(out/'geometry.csv',geo.values())
    write_json(out/'traversed_cells.json',cells)
    write_csv(out/'geometry_validation.csv',audit)
    return nodes,aircraft,boxes,dem,geo


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--raw',type=Path)
    parser.add_argument('--distance-method',choices=['aeqd_o01','wgs84_geodesic','haversine_6371000'])
    args=parser.parse_args()
    prepare(args.output,args.raw,args.distance_method)
    print('Original inputs and 15 exact DEM routes independently checked.')
