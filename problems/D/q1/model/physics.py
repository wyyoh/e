"""Appendix 2 and explicitly confirmed horizontal/climb parameterization."""
import json
import math
from scipy.optimize import brentq
from .io import ROOT

CONFIG=json.loads((ROOT/'data/model_config.json').read_text(encoding='utf-8'))
GRAVITY=CONFIG['gravity_mps2']
ENERGY_TOL=CONFIG['energy_tol_kwh']
TIME_TOL=CONFIG['time_tol_s']
MASS_TOL=CONFIG['mass_tol_kg']
VOLUME_TOL=CONFIG['volume_tol_m3']
THRESHOLD_TOL=CONFIG['threshold_tol']


def equivalent_range(m,q):
    if q < 0 or q > m.rated_kg:
        raise ValueError('Payload outside model domain')
    return m.empty_range_m-(m.empty_range_m-m.full_range_m)*(q/m.rated_kg)**1.5


def horizontal_energy(m,d,q):
    return m.battery_kwh*d/equivalent_range(m,q)


def climb_energy(m,q,h):
    if h < 0:
        raise ValueError('Negative climb')
    return (m.empty_kg+q)*GRAVITY*h/(m.up_eff*3.6e6)


def energy_parts(m,g,w):
    return dict(out_horizontal_kwh=horizontal_energy(m,g['distance_m'],w),
                out_climb_kwh=climb_energy(m,w,g['out_up_m']),
                back_horizontal_kwh=horizontal_energy(m,g['distance_m'],0),
                back_climb_kwh=climb_energy(m,0,g['back_up_m']))


def trip_energy(m,g,w):
    return math.fsum(energy_parts(m,g,w).values())


def time_parts(m,g,nbox):
    return dict(prep_s=m.prep_s, load_s=nbox*m.load_s,
                out_up_s=g['out_up_m']/m.up_mps, out_cruise_s=g['distance_m']/m.cruise_mps,
                out_down_s=g['out_down_m']/m.down_mps,
                handover_s=m.handover_s+nbox*m.handover_box_s,
                back_up_s=g['back_up_m']/m.up_mps, back_cruise_s=g['distance_m']/m.cruise_mps,
                back_down_s=g['back_down_m']/m.down_mps)


def trip_time(m,g,nbox):
    return math.fsum(time_parts(m,g,nbox).values())


def safe_payload(m,g,alpha):
    if not 0 <= alpha < 1:
        raise ValueError('Reserve must lie in [0,1)')
    budget=(1-alpha)*m.battery_kwh
    f=lambda w:trip_energy(m,g,w)-budget
    if f(0)>ENERGY_TOL:
        return dict(service_area=g['service_area'],aircraft_type=m.id,safe_payload_kg=None,
                    rated_payload_kg=m.rated_kg,energy_limited=True,empty_trip_feasible=False,
                    energy_at_safe_load_kwh=None,energy_budget_kwh=budget,return_soc=None)
    limited=f(m.rated_kg)>0
    if f(0)>=0:w=0.
    elif not limited:w=float(m.rated_kg)
    else:w=brentq(f,0,m.rated_kg,xtol=1e-12,rtol=1e-14)
    energy=trip_energy(m,g,w)
    return dict(service_area=g['service_area'],aircraft_type=m.id,safe_payload_kg=w,
                rated_payload_kg=m.rated_kg,energy_limited=limited,empty_trip_feasible=True,
                energy_at_safe_load_kwh=energy,energy_budget_kwh=budget,
                return_soc=1-energy/m.battery_kwh)


def bisection_payload(m,g,alpha):
    """Independent root algorithm (the end-to-end validator also redoes physics)."""
    budget=(1-alpha)*m.battery_kwh
    if trip_energy(m,g,0)>budget+ENERGY_TOL:return None
    lo,hi=0.,float(m.rated_kg)
    if trip_energy(m,g,hi)<=budget:return hi
    for _ in range(70):
        mid=(lo+hi)/2
        if trip_energy(m,g,mid)<=budget:lo=mid
        else:hi=mid
    return lo


def feasible(m,g,mass,volume,alpha):
    return (0 <= mass <= m.rated_kg and volume <= m.volume_m3+VOLUME_TOL
            and trip_energy(m,g,mass) <= (1-alpha)*m.battery_kwh+ENERGY_TOL)
