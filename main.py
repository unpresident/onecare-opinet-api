from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from pyproj import Transformer

app = FastAPI(title="OneCare Opinet API Engine")

# 브라우저 전면 허용 (CORS 충돌 방지)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPINET_API_KEY = "F261103068"

# WGS84 -> KATEC 좌표 변환 (오피넷 전용 Bessel 타원체)
def wgs84_to_katec(lat: float, lng: float):
    proj_wgs84 = "epsg:4326"
    proj_katec = "+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 +x_0=400000 +y_0=600000 +ellps=bessel +units=m +no_defs +towgs84=-146.43,507.89,681.46,0,0,0,0"
    transformer = Transformer.from_crs(proj_wgs84, proj_katec, always_xy=True)
    kx, ky = transformer.transform(lng, lat)
    return round(kx), round(ky)

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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        oil_list = data.get("RESULT", {}).get("OIL", [])
        stations = oil_list if isinstance(oil_list, list) else [oil_list] if oil_list else []
        
        if sort == "2":
            stations.sort(key=lambda x: float(x.get("DISTANCE", 0)))
        else:
            stations.sort(key=lambda x: float(x.get("PRICE", 0)))
            
        return {"status": "success", "count": len(stations[:20]), "stations": stations[:20]}
    except Exception as e:
        return {"status": "error", "message": str(e), "stations": []}
