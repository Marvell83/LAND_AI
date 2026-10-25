from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from land_radar.data_sources import SOURCES
from land_radar.geometry import bbox_for_cell
from land_radar.models import CellMetrics, HardRiskFlags, LandCell
from land_radar.pilot import SAKARYA_CANAKKALE, build_pilot_grid
from land_radar.providers.copernicus_stac import CopernicusSTACError, search_sentinel2_l2a
from land_radar.providers.osm import OSMProviderError, fetch_road_summary
from land_radar.scoring import score_cell


st.set_page_config(page_title="LAND RADAR", page_icon="🛰️", layout="wide")

st.title("LAND RADAR")
st.caption("Geospatial Investment Intelligence · V0.2 data-probe core")

st.info(
    "Kaynak yoksa katalizör yoktur. Geçmiş veri yoksa ivme yoktur. "
    "Fiyat verisi yoksa mispricing yoktur. Kanıt yoksa AI yorum yapmaz."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Pilot Grid", "Live Data Probe", "Research Lab", "Data Sources"]
)

with tab1:
    st.subheader("Sakarya → Çanakkale pilot koridoru")
    st.write(SAKARYA_CANAKKALE.note)
    cell_km = st.select_slider(
        "Hücre boyutu (km)",
        options=[1.0, 2.0, 5.0, 10.0],
        value=5.0,
        key="pilot_cell_km",
    )
    cells = build_pilot_grid(cell_km)
    c1, c2, c3 = st.columns(3)
    c1.metric("Pilot hücre sayısı", f"{len(cells):,}")
    c2.metric("Hücre boyutu", f"{cell_km:g} km")
    c3.metric("Durum", "Geometri hazır")
    st.warning(
        "Bu aşamada hücrelerde otomatik yatırım skoru yoktur. "
        "V0.2 gerçek kaynaklara kontrollü probe yapar; toplu tarama henüz kapalıdır."
    )
    st.dataframe(
        [
            {
                "cell_id": c.cell_id,
                "center_lat": c.center_lat,
                "center_lon": c.center_lon,
                "size_km": c.size_km,
            }
            for c in cells[:100]
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.subheader("Canlı veri probe")
    st.caption(
        "Tek bir pilot hücre için canlı kaynak erişimini test eder. "
        "Bu ekranın çıktısı henüz ana skora otomatik yazılmaz."
    )

    probe_km = st.select_slider(
        "Probe hücre boyutu (km)",
        options=[1.0, 2.0, 5.0, 10.0],
        value=5.0,
        key="probe_cell_km",
    )
    probe_cells = build_pilot_grid(probe_km)
    cell_index = int(
        st.number_input(
            "Hücre sıra numarası",
            min_value=0,
            max_value=max(0, len(probe_cells) - 1),
            value=0,
            step=1,
        )
    )
    selected = probe_cells[cell_index]
    bbox = bbox_for_cell(selected)

    st.write(
        {
            "cell_id": selected.cell_id,
            "center_lat": selected.center_lat,
            "center_lon": selected.center_lon,
            "bbox": [round(v, 6) for v in bbox],
        }
    )

    left, right = st.columns(2)

    with left:
        st.markdown("#### OpenStreetMap / Overpass")
        st.caption(
            "Yol varlığını ve yol sınıflarını test eder. "
            "En yakın ana yol değeri, yol geometrisine değil OSM way merkezine yaklaşık mesafedir."
        )
        if st.button("OSM yol probe çalıştır", use_container_width=True):
            try:
                road = fetch_road_summary(
                    bbox,
                    center_lat=selected.center_lat,
                    center_lon=selected.center_lon,
                )
                st.success("OSM yanıtı alındı.")
                a, b = st.columns(2)
                a.metric("Highway way", road.total_highway_ways)
                b.metric("Ana yol way", road.major_highway_ways)
                st.metric(
                    "Yaklaşık en yakın ana yol merkezi",
                    "—"
                    if road.nearest_major_way_center_km is None
                    else f"{road.nearest_major_way_center_km:.2f} km",
                )
                st.dataframe(
                    [{"highway": k, "count": v} for k, v in road.highway_classes],
                    use_container_width=True,
                    hide_index=True,
                )
            except OSMProviderError as exc:
                st.error(str(exc))

    with right:
        st.markdown("#### Copernicus STAC / Sentinel-2 L2A")
        default_end = date.today()
        default_start = default_end - timedelta(days=60)
        start_date = st.date_input("Başlangıç", value=default_start, key="stac_start")
        end_date = st.date_input("Bitiş", value=default_end, key="stac_end")
        cloud = st.slider("Azami bulut oranı (%)", 0, 100, 30)
        scene_limit = st.slider("Azami sahne", 1, 50, 20)

        if st.button("Sentinel-2 sahne ara", use_container_width=True):
            try:
                summary = search_sentinel2_l2a(
                    bbox,
                    start_date,
                    end_date,
                    max_cloud_cover=cloud,
                    limit=scene_limit,
                )
                st.success("Copernicus STAC yanıtı alındı.")
                a, b, c = st.columns(3)
                a.metric("Bulunan sahne", summary.count)
                b.metric(
                    "En düşük bulut",
                    "—"
                    if summary.min_cloud_cover is None
                    else f"%{summary.min_cloud_cover:.1f}",
                )
                c.metric(
                    "Medyan bulut",
                    "—"
                    if summary.median_cloud_cover is None
                    else f"%{summary.median_cloud_cover:.1f}",
                )
                st.dataframe(
                    [
                        {
                            "item_id": scene.item_id,
                            "datetime": scene.datetime,
                            "cloud_cover": scene.cloud_cover,
                        }
                        for scene in summary.scenes
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            except (CopernicusSTACError, ValueError) as exc:
                st.error(str(exc))

with tab3:
    st.subheader("Araştırma laboratuvarı")
    st.caption(
        "Buradaki girişler manuel senaryo testidir; gerçek bölge verisi değildir. "
        "Amaç skor ve veto davranışını test etmektir."
    )

    left, right = st.columns(2)
    with left:
        urban = st.slider("Urban Pressure", 0, 100, 50)
        accel = st.slider("Development Acceleration", 0, 100, 50)
        catalyst = st.slider("Catalyst Maturity", 0, 100, 50)
        story = st.slider("Story Maturity", 0, 100, 50)
        physical = st.slider("Physical Quality", 0, 100, 50)
    with right:
        have_price = st.checkbox("Fiyat verisi mevcut")
        mispricing = st.slider("Mispricing", 0, 100, 50, disabled=not have_price)
        exit_demand = st.slider("Exit Demand", 0, 100, 50)
        risk = st.slider("Risk", 0, 100, 20)
        confidence = st.slider("Data Confidence", 0, 100, 50)

    st.markdown("#### Hard-risk veto")
    r1, r2, r3, r4 = st.columns(4)
    legal = r1.checkbox("Kritik hukuki kısıt")
    flood = r2.checkbox("Çok yüksek taşkın")
    landslide = r3.checkbox("Çok yüksek heyelan")
    access = r4.checkbox("Hukuki yol erişimi yok")

    cell = LandCell(
        cell_id="MANUAL-TEST",
        center_lat=0.0,
        center_lon=0.0,
        metrics=CellMetrics(
            urban_pressure=urban,
            development_acceleration=accel,
            catalyst_maturity=catalyst,
            story_maturity=story,
            physical_quality=physical,
            mispricing=mispricing if have_price else None,
            exit_demand=exit_demand,
            risk=risk,
            confidence=confidence,
        ),
        hard_risks=HardRiskFlags(
            legal_restriction=legal,
            severe_flood=flood,
            severe_landslide=landslide,
            no_legal_access=access,
        ),
    )
    result = score_cell(cell)

    if result.blocked:
        st.error("DERİN İNCELEME BLOKE")
        st.write(" · ".join(result.block_reasons))
    else:
        a, b = st.columns(2)
        a.metric(
            "Transition Score",
            "—" if result.transition_score is None else f"{result.transition_score:.1f}",
        )
        b.metric(
            "Research Priority",
            "—"
            if result.research_priority_score is None
            else f"{result.research_priority_score:.1f}",
        )
        if result.missing_metrics:
            st.warning(
                "Araştırma öncelik puanı üretilmedi. Eksik: "
                + ", ".join(result.missing_metrics)
            )
        st.caption(
            "Research Priority ağırlıkları geçicidir ve backtest yapılmadan "
            "yatırım modeli olarak kabul edilmez."
        )

with tab4:
    st.subheader("Veri kaynağı kayıt defteri")
    st.dataframe(
        [
            {
                "Kaynak": source.name,
                "Kategori": source.category,
                "Amaç": source.purpose,
                "Durum": source.status,
                "Point-in-time": "Evet" if source.point_in_time_required else "Hayır",
            }
            for source in SOURCES
        ],
        use_container_width=True,
        hide_index=True,
    )
