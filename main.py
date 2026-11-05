import math
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(title="OneCare Opinet API Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPINET_API_KEY = "F261103068"

def wgs84_to_katec(lat: float, lng: float):
    """
    pyproj C-바인딩 에러를 완벽 방지하는 순수 파이썬 KATEC(TM128) 변환 수식
    """
    try:
        phi = math.radians(lat)
        lam = math.radians(lng)

        a = 6377397.155  # Bessel 1841 장반경
        f = 1.0 / 299.1528128
        e2 = 2 * f - f * f
        e_prime2 = e2 / (1.0 - e2)

        phi0 = math.radians(38.0)
        lam0 = math.radians(128.0)
        k0 = 0.9999
        x0 = 400000.0
        y0 = 600000.0

        def calc_m(p):
            return a * (
                (1.0 - e2 / 4.0 - 3.0 * e2**2 / 64.0 - 5.0 * e2**3 / 256.0) * p
                - (3.0 * e2 / 8.0 + 3.0 * e2**2 / 32.0 + 45.0 * e2**3 / 1024.0) * math.sin(2.0 * p)
                + (15.0 * e2**2 / 256.0 + 45.0 * e2**3 / 1024.0) * math.sin(4.0 * p)
                - (35.0 * e2**3 / 3072.0) * math.sin(6.0 * p)
            )

        m = calc_m(phi)
        m0 = calc_m(phi0)

        n = a / math.sqrt(1.0 - e2 * math.sin(phi)**2)
        t = math.tan(phi)**2
        c = e_prime2 * math.cos(phi)**2
        al = (lam - lam0) * math.cos(phi)

        kx = x0 + k0 * n * (
            al + (1.0 - t + c) * (al**3) / 6.0
            + (5.0 - 18.0 * t + t**2 + 72.0 * c - 58.0 * e_prime2) * (al**5) / 120.0
        )
        ky = y0 + k0 * (
            m - m0 + n * math.tan(phi) * (
                (al**2) / 2.0
                + (5.0 - t + 9.0 * c + 4.0 * c**2) * (al**4) / 24.0
                + (61.0 - 58.0 * t + t**2 + 600.0 * c - 330.0 * e_prime2) * (al**6) / 720.0
            )
        )
        return int(round(kx)), int(round(ky))
    except Exception:
        # 비상 시 대구 중심 기본 KATEC 좌표
        return 457200, 363500

@app.get("/")
def health_check():
    return {"status": "ok", "message": "원스탑 모빌리티 원케어 오피넷 API 정상 가동 중"}

@app.get("/api/opinet")
def get_opinet_stations(
    lat: float = Query(35.8888),
    lng: float = Query(128.6288),
    prodcd: str = Query("D047"),
    radius: str = Query("10000"),
    sort: str = Query("1")
):
    try:
        kx, ky = wgs84_to_katec(lat, lng)

        url = "https://www.opinet.co.kr/api/aroundAll.do"
        params = {
            "out": "json",
            "code": OPINET_API_KEY,
            "x": kx,
            "y": ky,
            "radius": radius,
            "sort": sort,
            "prodcd": prodcd
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()

        result_node = data.get("RESULT", {})
        oil_list = result_node.get("OIL", [])

        stations = []
        if isinstance(oil_list, list):
            stations = oil_list
        elif isinstance(oil_list, dict):
            stations = [oil_list]

        if sort == "2":
            stations.sort(key=lambda x: float(x.get("DISTANCE", 0) or 0))
        else:
            stations.sort(key=lambda x: float(x.get("PRICE", 0) or 0))

        return {"status": "success", "count": len(stations[:20]), "stations": stations[:20]}
    except Exception as e:
        return {"status": "error", "message": str(e), "stations": []}
