from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from land_radar import __version__
from land_radar.candidate_funnel import CandidatePolicy, build_candidate_funnel, surviving_candidates
from land_radar.catalyst import STAGE_LABELS
from land_radar.config import resolve_cdse_credentials
from land_radar.data_sources import SOURCES
from land_radar.geometry import bbox_for_cell
from land_radar.inflation import CPIIndex, InflationDataError, add_real_price_columns
from land_radar.models import CellMetrics, HardRiskFlags, LandCell
from land_radar.pilot import SAKARYA_CANAKKALE, build_pilot_grid
from land_radar.plan_import import PlanImportError, import_plan_csv
from land_radar.planning_scan import run_planning_scan
from land_radar.pricing import PriceDataError, comparable_gap, expected_csv_columns, prepare_price_data, summarize_comparables
from land_radar.providers.copernicus_dem import CopernicusDEMError, CopernicusProcessClient
from land_radar.providers.copernicus_stac import CopernicusSTACError, search_sentinel2_l2a
from land_radar.providers.ghsl import GHSLProviderError, compare_built_up, discover_epoch_file, summarize_built_up
from land_radar.providers.aygm_rail import AYGMRailProviderError, fetch_rail_projects, filter_project_keywords, record_to_catalyst as rail_record_to_catalyst
from land_radar.providers.osbuk import OSBUKProviderError, fetch_osb_list, filter_provinces, record_to_catalyst
from land_radar.providers.osm import OSMProviderError, fetch_road_summary
from land_radar.providers.osm_geometry import OSMGeometryProviderError, best_name_matches, fetch_industrial_geometries, fetch_rail_geometries, to_geometry_evidence
from land_radar.providers.sentinel_surface import SentinelSurfaceClient, SentinelSurfaceError, compare_surface
from land_radar.providers.arcgis_geojson import ArcGISGeoJSONError
from land_radar.providers.tarimorman_official import fetch_flood_hazards, fetch_protected_constraints
from land_radar.readiness import check_data_readiness
from land_radar.scoring import score_cell
from land_radar.spatial.batch import batch_link_catalysts
from land_radar.spatial.catalyst_geometry import link_catalyst_to_cell
from land_radar.spatial.distance import distance_from_cell_to_geometry
from land_radar.spatial.geometry import geometry_from_geojson
from land_radar.spatial.hazard_overlap import batch_link_hazards, summarize_cell_hazards
from land_radar.spatial.hazard_registry import hazards_from_feature_collection
from land_radar.spatial.influence import classify_influence
from land_radar.spatial.planning_overlap import batch_link_constraints, summarize_cell_planning
from land_radar.spatial.registry import registry_from_feature_collection, registry_to_feature_collection
from land_radar.terrain_scan import scan_terrain
from land_radar.urban_scan import rank_accelerating, scan_grid_ghsl


st.set_page_config(page_title="LAND RADAR", page_icon="🛰️", layout="wide")

st.title("LAND RADAR")
st.caption(f"Geospatial Investment Intelligence · v{__version__}")

st.info(
    "Kaynak yoksa katalizör yoktur. Geçmiş veri yoksa ivme yoktur. "
    "Fiyat verisi yoksa mispricing yoktur. Kanıt yoksa AI yorum yapmaz."
)

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "Pilot Grid",
        "Live Data Probe",
        "Spatial Intelligence",
        "Price Lab",
        "Planning Intelligence",
        "Risk & Funnel",
        "Research Lab",
        "Data Sources",
    ]
)

with tab1:
    st.subheader("Sakarya → Çanakkale pilot koridoru")
    st.write(SAKARYA_CANAKKALE.note)

    with st.expander("Data Readiness", expanded=True):
        try:
            readiness_secret_map = st.secrets.to_dict()
        except Exception:
            readiness_secret_map = {}
        readiness_credentials = resolve_cdse_credentials(readiness_secret_map)
        readiness = check_data_readiness(
            cdse_credentials_available=readiness_credentials is not None,
        )
        readiness_df = pd.DataFrame(
            [
                {
                    "key": item.key,
                    "status": item.status,
                    "required": item.required,
                    "detail": item.detail,
                }
                for item in readiness.items
            ]
        )
        st.dataframe(
            readiness_df,
            use_container_width=True,
            hide_index=True,
        )
        if readiness.required_ready:
            st.success("Zorunlu GHSL çekirdeği hazır.")
        else:
            st.warning(
                "Gerçek GHSL taraması için zorunlu epoch dosyaları eksik. "
                "Eksik veri LOW olarak yorumlanmaz."
            )
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
        "Toplu tarama artık Risk & Funnel sekmesinde kontrollü olarak çalıştırılabilir."
    )
    pilot_rows = [
        {
            "cell_id": c.cell_id,
            "lat": c.center_lat,
            "lon": c.center_lon,
            "size_km": c.size_km,
        }
        for c in cells[:500]
    ]
    pilot_df = pd.DataFrame(pilot_rows)
    st.map(pilot_df, latitude="lat", longitude="lon")
    st.dataframe(
        pilot_df.head(100),
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

    st.divider()
    st.markdown("#### Copernicus DEM GLO-90 · yükseklik ve eğim")
    try:
        secret_map = st.secrets.to_dict()
    except Exception:
        secret_map = {}
    cdse_credentials = resolve_cdse_credentials(secret_map)

    if cdse_credentials is None:
        st.warning(
            "DEM probe için CDSE OAuth bilgisi bulunamadı. "
            "CDSE_CLIENT_ID ve CDSE_CLIENT_SECRET ortam değişkenlerini veya "
            ".streamlit/secrets.toml dosyasını kullan."
        )
    else:
        st.success(f"CDSE OAuth hazır · kaynak: {cdse_credentials.source}")
        if st.button("Copernicus DEM probe çalıştır", use_container_width=True):
            try:
                dem_client = CopernicusProcessClient(
                    cdse_credentials.client_id,
                    cdse_credentials.client_secret,
                )
                terrain = dem_client.terrain_summary(
                    bbox,
                    dem_instance="COPERNICUS_90",
                )
                a, b, c = st.columns(3)
                a.metric("Ortalama yükselti", f"{terrain.mean_elevation_m:.0f} m")
                b.metric("Ortalama eğim", f"{terrain.mean_slope_deg:.2f}°")
                c.metric("P90 eğim", f"{terrain.p90_slope_deg:.2f}°")
                st.write(
                    {
                        "min_elevation_m": terrain.min_elevation_m,
                        "max_elevation_m": terrain.max_elevation_m,
                        "max_slope_deg": terrain.max_slope_deg,
                        "valid_pixels": terrain.valid_pixels,
                        "dem_instance": terrain.dem_instance,
                    }
                )
            except CopernicusDEMError as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("#### Sentinel-2 iki dönem yüzey değişimi")
    st.caption(
        "Aynı mevsime yakın iki zaman penceresini karşılaştır. "
        "NDVI/NDBI/BSI ve SCL sınıf payları ayrı gösterilir; sonuç doğrudan 'yapılaşma' sayılmaz."
    )
    default_second_end = date.today()
    default_second_start = default_second_end - timedelta(days=60)
    default_first_end = default_second_end - timedelta(days=365)
    default_first_start = default_second_start - timedelta(days=365)

    p1a, p1b, p2a, p2b = st.columns(4)
    first_start = p1a.date_input(
        "1. dönem başlangıç",
        value=default_first_start,
        key="surface_first_start",
    )
    first_end = p1b.date_input(
        "1. dönem bitiş",
        value=default_first_end,
        key="surface_first_end",
    )
    second_start = p2a.date_input(
        "2. dönem başlangıç",
        value=default_second_start,
        key="surface_second_start",
    )
    second_end = p2b.date_input(
        "2. dönem bitiş",
        value=default_second_end,
        key="surface_second_end",
    )
    surface_cloud = st.slider(
        "Yüzey değişimi için azami tile bulut oranı (%)",
        0,
        100,
        30,
        key="surface_cloud",
    )

    if st.button("Sentinel yüzey değişimini hesapla", use_container_width=True):
        if cdse_credentials is None:
            st.warning("Sentinel Process API için CDSE OAuth bilgisi gerekli.")
        else:
            try:
                surface_client = SentinelSurfaceClient(
                    cdse_credentials.client_id,
                    cdse_credentials.client_secret,
                )
                first_surface = surface_client.summary(
                    bbox,
                    first_start,
                    first_end,
                    max_cloud_coverage=surface_cloud,
                )
                second_surface = surface_client.summary(
                    bbox,
                    second_start,
                    second_end,
                    max_cloud_coverage=surface_cloud,
                )
                surface_change = compare_surface(first_surface, second_surface)

                st.dataframe(
                    [
                        {
                            "period": "1",
                            "start": first_surface.start_date,
                            "end": first_surface.end_date,
                            "median_ndvi": first_surface.median_ndvi,
                            "median_ndbi": first_surface.median_ndbi,
                            "median_bsi": first_surface.median_bsi,
                            "vegetation_share": first_surface.vegetation_share,
                            "bare_soil_share": first_surface.bare_soil_share,
                            "water_share": first_surface.water_share,
                            "valid_land_pixels": first_surface.valid_land_pixels,
                        },
                        {
                            "period": "2",
                            "start": second_surface.start_date,
                            "end": second_surface.end_date,
                            "median_ndvi": second_surface.median_ndvi,
                            "median_ndbi": second_surface.median_ndbi,
                            "median_bsi": second_surface.median_bsi,
                            "vegetation_share": second_surface.vegetation_share,
                            "bare_soil_share": second_surface.bare_soil_share,
                            "water_share": second_surface.water_share,
                            "valid_land_pixels": second_surface.valid_land_pixels,
                        },
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("##### Ham değişim")
                st.write(
                    {
                        "delta_ndvi": surface_change.delta_ndvi,
                        "delta_ndbi": surface_change.delta_ndbi,
                        "delta_bsi": surface_change.delta_bsi,
                        "delta_vegetation_share_pp": surface_change.delta_vegetation_share_pp,
                        "delta_bare_soil_share_pp": surface_change.delta_bare_soil_share_pp,
                        "delta_water_share_pp": surface_change.delta_water_share_pp,
                    }
                )
                st.warning(
                    "Bu çıktılar spektral/sınıfsal değişim kanıtıdır. "
                    "Tek başına yeni yapılaşma veya yatırım fırsatı hükmü vermez."
                )
            except (SentinelSurfaceError, ValueError) as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("#### GHSL GHS-BUILT-S · yerel raster analizi")
    st.caption(
        "GHSL R2023A dönemleri yapısal tarihsel baz sağlar. "
        "Resmî ürün dönemleri interpolasyon/ekstrapolasyon içerdiği için "
        "bunları doğrudan yıllık gözlem gibi yorumlamıyoruz; güncel değişimi Sentinel ile teyit ediyoruz."
    )
    ghsl_dir_text = st.text_input(
        "GHSL GeoTIFF klasörü",
        value="data/raw/ghsl",
        help="İndirilip ZIP'ten çıkarılmış resmî GHS-BUILT-S GeoTIFF dosyalarının bulunduğu klasör.",
    )
    ghsl_epochs = [2010, 2015, 2020]
    if st.button("Seçili hücre için GHSL dönemlerini analiz et", use_container_width=True):
        ghsl_dir = Path(ghsl_dir_text)
        summaries = []
        missing_epochs = []
        try:
            for epoch in ghsl_epochs:
                path = discover_epoch_file(ghsl_dir, epoch)
                if path is None:
                    missing_epochs.append(epoch)
                    continue
                summaries.append(summarize_built_up(path, bbox))

            if not summaries:
                st.warning(
                    "Uyumlu GHSL GeoTIFF bulunamadı. 2010/2015/2020 epoch dosyalarını "
                    "belirtilen klasöre çıkar."
                )
            else:
                st.dataframe(
                    [
                        {
                            "epoch": s.epoch,
                            "total_built_up_m2": s.total_built_up_m2,
                            "mean_m2_per_pixel": s.mean_built_up_m2_per_pixel,
                            "occupied_pixel_share": s.occupied_pixel_share,
                            "valid_pixels": s.valid_pixels,
                            "source": s.source_path,
                        }
                        for s in summaries
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
                if missing_epochs:
                    st.warning("Eksik GHSL dönemleri: " + ", ".join(map(str, missing_epochs)))

                ordered = sorted(
                    [s for s in summaries if s.epoch is not None],
                    key=lambda s: s.epoch,
                )
                changes = [
                    compare_built_up(ordered[i - 1], ordered[i])
                    for i in range(1, len(ordered))
                ]
                if changes:
                    st.markdown("##### Dönemsel built-up değişimi")
                    st.dataframe(
                        [
                            {
                                "period": f"{c.start_epoch}→{c.end_epoch}",
                                "absolute_change_m2": c.absolute_change_m2,
                                "percent_change": c.percent_change,
                                "occupied_share_change_pp": c.occupied_share_change_pp,
                            }
                            for c in changes
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
        except GHSLProviderError as exc:
            st.error(str(exc))

    st.markdown("##### Kontrollü GHSL grid taraması")
    scan_limit = st.select_slider(
        "Taranacak ilk hücre sayısı",
        options=[25, 50, 100, 250, 500],
        value=50,
        key="ghsl_scan_limit",
    )
    st.caption(
        "Bu tarama yalnız GHSL built-up ivmesini sıralar. "
        "Fiyat, risk veya katalizör içermediği için yatırım sıralaması değildir."
    )
    if st.button("GHSL grid taramasını çalıştır", use_container_width=True):
        try:
            scan_records = scan_grid_ghsl(
                probe_cells,
                ghsl_dir_text,
                limit=scan_limit,
            )
            ranked = rank_accelerating(scan_records)
            st.success(f"{len(scan_records)} hücre tarandı.")
            ranked_rows = [
                {
                    "rank": i + 1,
                    "cell_id": r.cell_id,
                    "lat": r.center_lat,
                    "lon": r.center_lon,
                    "built_2010_m2": r.built_2010_m2,
                    "built_2015_m2": r.built_2015_m2,
                    "built_2020_m2": r.built_2020_m2,
                    "cagr_10_15_pct": r.cagr_2010_2015_pct,
                    "cagr_15_20_pct": r.cagr_2015_2020_pct,
                    "acceleration_pp_year": r.acceleration_pp_per_year,
                    "occupied_accel_pp": r.occupied_share_acceleration_pp,
                    "signal": r.signal,
                }
                for i, r in enumerate(ranked)
            ]
            ranked_df = pd.DataFrame(ranked_rows)
            top_df = ranked_df.head(30)
            st.map(top_df, latitude="lat", longitude="lon")
            st.dataframe(
                top_df,
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "GHSL tarama sonucunu CSV indir",
                data=ranked_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="land_radar_ghsl_scan.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except (GHSLProviderError, ValueError) as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("#### Resmî korunan alan + USBS taşkın probe")
    st.caption(
        "Tarım ve Orman Bakanlığı açık ArcGIS REST servislerini doğrudan sorgular. "
        "Korunan alan kesişimi otomatik hard-veto değildir; hukukî inceleme işaretidir."
    )
    if st.button("Resmî kısıt ve taşkın probe çalıştır", use_container_width=True):
        official_bbox = bbox_for_cell(selected, padding_km=20.0)
        try:
            protected_constraints = fetch_protected_constraints(official_bbox)
            protected_links = batch_link_constraints(
                [selected],
                protected_constraints,
                max_distance_km=20.0,
            )
            planning_summary = summarize_cell_planning(
                selected.cell_id,
                protected_links,
                checked=True,
            )

            flood_hazards = fetch_flood_hazards(official_bbox)
            flood_links = batch_link_hazards(
                [selected],
                flood_hazards,
                max_distance_km=20.0,
            )
            flood_summary = summarize_cell_hazards(
                selected.cell_id,
                flood_links,
            )

            a, b, c1, d = st.columns(4)
            a.metric("Korunan alan bulgusu", planning_summary.finding_count)
            b.metric("Hücreyle kesişen", planning_summary.intersecting_count)
            c1.metric(
                "Hukukî inceleme",
                "EVET" if planning_summary.legal_review_required else "Hayır",
            )
            d.metric("Taşkın risk bulgusu", flood_summary.finding_count)

            if protected_links:
                st.markdown("##### Korunan alan bağlantıları")
                st.dataframe(
                    [
                        {
                            "category": link.category,
                            "distance_km": link.distance_km,
                            "intersects": link.intersects_cell,
                            "overlap_ratio": link.overlap_ratio,
                            "legal_effect": int(link.legal_effect),
                            "source": link.source,
                        }
                        for link in protected_links
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            if flood_links:
                st.markdown("##### USBS taşkın bağlantıları")
                st.dataframe(
                    [
                        {
                            "hazard_id": link.hazard_id,
                            "distance_km": link.distance_km,
                            "intersects": link.intersects_cell,
                            "overlap_ratio": link.overlap_ratio,
                            "severity": int(link.severity),
                            "source": link.source,
                        }
                        for link in flood_links
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            if not protected_links and not flood_links:
                st.success(
                    "20 km bağlamında bu iki resmî servis üzerinden bir bulgu dönmedi. "
                    "Bu sonuç e-Plan, AFAD/heyelan veya diğer hukukî katmanların temiz olduğu anlamına gelmez."
                )
        except (ArcGISGeoJSONError, ValueError) as exc:
            st.error(str(exc))

with tab3:
    st.subheader("Spatial Intelligence")
    st.caption(
        "Katalizör statüsü ile katalizör geometrisi ayrı kanıt olarak tutulur. "
        "OSM yalnız geometri bağlamıdır; OSBÜK/AYGM resmî statüsünün yerine geçmez."
    )

    s1, s2, s3 = st.columns(3)
    spatial_km = s1.select_slider(
        "Spatial hücre boyutu (km)",
        options=[1.0, 2.0, 5.0, 10.0],
        value=5.0,
        key="spatial_cell_km",
    )
    spatial_cells = build_pilot_grid(spatial_km)
    spatial_index = int(
        s2.number_input(
            "Spatial hücre sıra numarası",
            min_value=0,
            max_value=max(0, len(spatial_cells) - 1),
            value=0,
            step=1,
            key="spatial_cell_index",
        )
    )
    padding_km = float(
        s3.number_input(
            "Geometri arama tamponu (km)",
            min_value=1.0,
            max_value=50.0,
            value=20.0,
            step=1.0,
        )
    )

    spatial_cell = spatial_cells[spatial_index]
    spatial_bbox = bbox_for_cell(spatial_cell)
    search_bbox = bbox_for_cell(spatial_cell, padding_km=padding_km)

    st.write(
        {
            "cell_id": spatial_cell.cell_id,
            "center_lat": spatial_cell.center_lat,
            "center_lon": spatial_cell.center_lon,
            "cell_bbox": [round(v, 6) for v in spatial_bbox],
            "search_bbox": [round(v, 6) for v in search_bbox],
        }
    )

    st.map(
        pd.DataFrame(
            [
                {
                    "lat": spatial_cell.center_lat,
                    "lon": spatial_cell.center_lon,
                }
            ]
        ),
        latitude="lat",
        longitude="lon",
    )

    def _spatial_rows(features):
        rows = []
        map_rows = [
            {
                "kind": "cell",
                "name": spatial_cell.cell_id,
                "lat": spatial_cell.center_lat,
                "lon": spatial_cell.center_lon,
            }
        ]
        for feature in features:
            evidence = to_geometry_evidence(feature)
            distance = distance_from_cell_to_geometry(spatial_cell, evidence)
            band = classify_influence(
                distance.distance_km,
                intersects_cell=distance.intersects_cell,
            )
            geom = geometry_from_geojson(feature.geometry_geojson)
            centroid = geom.centroid
            rows.append(
                {
                    "name": feature.name,
                    "osm_id": feature.feature_id,
                    "geometry_role": feature.geometry_role,
                    "geometry_confidence": feature.confidence,
                    "distance_km": distance.distance_km,
                    "intersects_cell": distance.intersects_cell,
                    "influence": band.code,
                    "influence_label": band.label,
                    "railway": feature.tags.get("railway"),
                    "landuse": feature.tags.get("landuse"),
                    "industrial": feature.tags.get("industrial"),
                }
            )
            map_rows.append(
                {
                    "kind": "feature",
                    "name": feature.name,
                    "lat": float(centroid.y),
                    "lon": float(centroid.x),
                }
            )
        rows.sort(key=lambda row: row["distance_km"])
        return rows, map_rows

    left_spatial, right_spatial = st.columns(2)

    with left_spatial:
        st.markdown("#### OSM sanayi geometrileri")
        if st.button("Yakındaki sanayi geometrilerini getir", use_container_width=True):
            try:
                industrial_features = fetch_industrial_geometries(search_bbox)
                industrial_rows, industrial_map = _spatial_rows(industrial_features)
                st.success(f"{len(industrial_rows)} isimli sanayi geometrisi bulundu.")
                if industrial_rows:
                    st.map(
                        pd.DataFrame(industrial_map),
                        latitude="lat",
                        longitude="lon",
                    )
                    st.dataframe(
                        pd.DataFrame(industrial_rows).head(100),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Bu arama alanında isimli sanayi geometrisi bulunmadı.")
            except OSMGeometryProviderError as exc:
                st.error(str(exc))

    with right_spatial:
        st.markdown("#### OSM demiryolu geometrileri")
        if st.button("Yakındaki demiryolu geometrilerini getir", use_container_width=True):
            try:
                rail_features = fetch_rail_geometries(search_bbox)
                rail_rows, rail_map = _spatial_rows(rail_features)
                st.success(f"{len(rail_rows)} demiryolu geometrisi bulundu.")
                if rail_rows:
                    st.map(
                        pd.DataFrame(rail_map),
                        latitude="lat",
                        longitude="lon",
                    )
                    st.dataframe(
                        pd.DataFrame(rail_rows).head(100),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Bu arama alanında demiryolu geometrisi bulunmadı.")
            except OSMGeometryProviderError as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("#### OSB statüsü + geometri kanıtı eşleştirme")
    st.caption(
        "Bu otomatik eşleştirme yalnız aday üretir. İsim benzerliği ve geometri kaynağı "
        "ayrı gösterilir; düşük benzerlikler resmî eşleşme sayılmaz."
    )
    if st.button("Yakındaki OSB adaylarını eşleştir", use_container_width=True):
        try:
            industrial_features = fetch_industrial_geometries(search_bbox)
            osb_records = filter_provinces(
                fetch_osb_list(),
                ["Sakarya", "Bursa", "Balıkesir", "Çanakkale"],
            )
            linked_rows = []
            for record in osb_records:
                matches = best_name_matches(
                    f"{record.province} {record.name}",
                    industrial_features,
                    minimum_score=0.40,
                    limit=1,
                )
                if not matches:
                    continue

                feature, similarity = matches[0]
                catalyst = record_to_catalyst(record)
                geometry_evidence = to_geometry_evidence(feature)
                link = link_catalyst_to_cell(
                    catalyst,
                    geometry_evidence,
                    spatial_cell,
                )
                linked_rows.append(
                    {
                        "osb": record.name,
                        "province": record.province,
                        "official_status": record.status,
                        "catalyst_stage": link.catalyst_stage,
                        "status_confidence": link.status_evidence_confidence,
                        "osm_feature": feature.name,
                        "name_similarity": similarity,
                        "geometry_role": feature.geometry_role,
                        "geometry_confidence": link.geometry_confidence,
                        "distance_km": link.distance_km,
                        "influence": link.influence_code,
                        "evidence_complete": link.evidence_complete,
                    }
                )

            linked_rows.sort(
                key=lambda row: (
                    -row["name_similarity"],
                    row["distance_km"],
                )
            )
            if linked_rows:
                st.dataframe(
                    pd.DataFrame(linked_rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(
                    "Bu hücre çevresindeki OSM sanayi isimleriyle güvenli bir OSB isim eşleşmesi bulunmadı."
                )
        except (OSMGeometryProviderError, OSBUKProviderError, ValueError) as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("#### Geometry Registry · GeoJSON")
    st.caption(
        "Resmî veya manuel doğrulanmış geometriyi katalizör kimliğiyle saklamak için. "
        "Registry geometrisi statü kanıtının yerine geçmez."
    )

    registry_template = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [29.0, 40.0],
                },
                "properties": {
                    "catalyst_id": "osb:il:osb-adi",
                    "source": "official-or-manual-source",
                    "feature_name": "OSB adı",
                    "observed_date": date.today().isoformat(),
                    "source_url": None,
                    "feature_id": "source-feature-id",
                    "confidence": 90,
                    "geometry_role": "official_boundary_or_point",
                    "manual_verified": False,
                },
            }
        ],
    }
    st.download_button(
        "Geometry Registry GeoJSON şablonunu indir",
        data=json.dumps(
            registry_template,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        file_name="land_radar_geometry_registry_template.geojson",
        mime="application/geo+json",
    )

    registry_upload = st.file_uploader(
        "Geometry Registry GeoJSON yükle",
        type=["geojson", "json"],
        key="geometry_registry_upload",
    )

    if registry_upload is not None:
        try:
            registry_payload = json.load(registry_upload)
            registry_entries = registry_from_feature_collection(
                registry_payload
            )
            st.success(f"{len(registry_entries)} geometri registry kaydı doğrulandı.")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "catalyst_id": entry.catalyst_id,
                            "feature_name": entry.evidence.feature_name,
                            "source": entry.evidence.source,
                            "geometry_role": entry.evidence.geometry_role,
                            "geometry_confidence": entry.evidence.confidence,
                            "manual_verified": entry.manual_verified,
                            "observed_date": entry.evidence.observed_date,
                        }
                        for entry in registry_entries
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

            batch_limit = st.select_slider(
                "Registry batch hücre sayısı",
                options=[25, 50, 100, 250],
                value=50,
                key="registry_batch_limit",
            )
            batch_max_distance = st.slider(
                "Batch azami katalizör mesafesi (km)",
                min_value=1,
                max_value=50,
                value=20,
                key="registry_batch_distance",
            )

            if st.button(
                "Registry'yi pilot hücrelere bağla",
                use_container_width=True,
            ):
                catalyst_map = {}

                try:
                    for record in filter_provinces(
                        fetch_osb_list(),
                        ["Sakarya", "Bursa", "Balıkesir", "Çanakkale"],
                    ):
                        catalyst = record_to_catalyst(record)
                        catalyst_map[catalyst.catalyst_id] = catalyst
                except OSBUKProviderError as exc:
                    st.warning(f"OSBÜK katalizörleri alınamadı: {exc}")

                try:
                    for record in fetch_rail_projects():
                        catalyst = rail_record_to_catalyst(record)
                        catalyst_map[catalyst.catalyst_id] = catalyst
                except AYGMRailProviderError as exc:
                    st.warning(f"AYGM katalizörleri alınamadı: {exc}")

                batch_result = batch_link_catalysts(
                    spatial_cells[:batch_limit],
                    catalyst_map,
                    registry_entries,
                    max_distance_km=float(batch_max_distance),
                )

                link_rows = [
                    {
                        "cell_id": link.cell_id,
                        "catalyst_id": link.catalyst_id,
                        "catalyst_name": link.catalyst_name,
                        "category": link.catalyst_category,
                        "stage": link.catalyst_stage,
                        "status_confidence": link.status_evidence_confidence,
                        "geometry_source": link.geometry_source,
                        "geometry_confidence": link.geometry_confidence,
                        "distance_km": link.distance_km,
                        "intersects": link.intersects_cell,
                        "influence": link.influence_code,
                    }
                    for link in batch_result.links
                ]
                if link_rows:
                    st.dataframe(
                        pd.DataFrame(link_rows),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.download_button(
                        "Spatial batch sonuçlarını CSV indir",
                        data=pd.DataFrame(link_rows)
                        .to_csv(index=False)
                        .encode("utf-8-sig"),
                        file_name="land_radar_spatial_links.csv",
                        mime="text/csv",
                    )
                else:
                    st.info(
                        "Seçilen hücre/mesafe sınırında registry katalizör bağlantısı bulunmadı."
                    )

                if batch_result.missing_catalysts:
                    st.warning(
                        "Registry'de olup mevcut statü akışında bulunmayan catalyst_id: "
                        + ", ".join(batch_result.missing_catalysts[:20])
                    )
                if batch_result.missing_geometries:
                    st.caption(
                        "Statüsü olup registry geometrisi bulunmayan katalizör sayısı: "
                        f"{len(batch_result.missing_geometries)}"
                    )

        except (ValueError, json.JSONDecodeError) as exc:
            st.error(f"Geometry Registry okunamadı: {exc}")


with tab4:
    st.subheader("Emsal Fiyat Laboratuvarı")
    st.caption(
        "Bu ekran emsal veri dağılımını analiz eder. Sonuç 'gerçek değer' veya "
        "'yatırım tavsiyesi' değildir; emsal medyanına göre fiyat farkını gösterir."
    )

    template_df = pd.DataFrame(
        [
            {
                "observed_date": "2026-10-01",
                "price_tl": 1500000,
                "area_m2": 2000,
                "source_type": "asking",
                "lat": 40.0000,
                "lon": 29.0000,
                "land_type": "tarla",
                "province": "Balıkesir",
                "district": "Örnek",
                "neighborhood": "Örnek",
                "listing_id": "sample-1",
            }
        ],
        columns=list(expected_csv_columns()),
    )
    st.download_button(
        "Emsal CSV şablonunu indir",
        data=template_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="land_radar_price_template.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader(
        "Emsal CSV yükle",
        type=["csv"],
        key="price_csv",
    )

    cpi_template = pd.DataFrame(
        [
            {"date": "2025-07-01", "index": 100.0},
            {"date": "2026-07-01", "index": 130.0},
        ]
    )
    st.download_button(
        "TÜFE/CPI CSV şablonunu indir",
        data=cpi_template.to_csv(index=False).encode("utf-8-sig"),
        file_name="land_radar_cpi_template.csv",
        mime="text/csv",
    )
    cpi_uploaded = st.file_uploader(
        "TÜFE/CPI CSV yükle (opsiyonel)",
        type=["csv"],
        key="cpi_csv",
        help="date,index sütunları gerekir. Verilirse emsaller analiz tarihinin fiyat düzeyine taşınır.",
    )

    p1, p2, p3 = st.columns(3)
    as_of = p1.date_input("Analiz tarihi", value=date.today(), key="price_as_of")
    max_age = p2.number_input(
        "Azami emsal yaşı (gün)",
        min_value=30,
        max_value=3650,
        value=730,
        step=30,
    )
    land_type_filter = p3.text_input(
        "Arazi türü filtresi (opsiyonel)",
        value="",
        placeholder="tarla / arsa",
    )

    geo_filter = st.checkbox("Konu parsele göre mesafe filtresi kullan")
    subject_lat = subject_lon = max_distance = None
    if geo_filter:
        g1, g2, g3 = st.columns(3)
        subject_lat = g1.number_input(
            "Konu enlem",
            min_value=-90.0,
            max_value=90.0,
            value=40.0000,
            format="%.6f",
        )
        subject_lon = g2.number_input(
            "Konu boylam",
            min_value=-180.0,
            max_value=180.0,
            value=29.0000,
            format="%.6f",
        )
        max_distance = g3.number_input(
            "Azami mesafe (km)",
            min_value=0.1,
            max_value=100.0,
            value=10.0,
            step=0.5,
        )

    if uploaded is not None:
        try:
            price_df = pd.read_csv(uploaded, sep=None, engine="python")
            price_basis = "nominal"

            if cpi_uploaded is not None:
                # Filter invalid/future/out-of-scope observations before CPI lookup,
                # but postpone outlier trimming until all prices share one price level.
                filtered, input_rows = prepare_price_data(
                    price_df,
                    as_of_date=as_of,
                    max_age_days=int(max_age),
                    subject_lat=subject_lat,
                    subject_lon=subject_lon,
                    max_distance_km=max_distance,
                    land_type=land_type_filter.strip() or None,
                    apply_outlier_filter=False,
                )
                cpi_df = pd.read_csv(cpi_uploaded, sep=None, engine="python")
                cpi_index = CPIIndex.from_frame(cpi_df)
                adjusted = add_real_price_columns(
                    filtered,
                    cpi_index,
                    reference_date=as_of,
                )
                adjusted["nominal_price_tl"] = adjusted["price_tl"]
                adjusted["nominal_price_per_m2"] = (
                    adjusted["price_tl"] / adjusted["area_m2"]
                )
                adjusted["price_tl"] = adjusted["real_price_tl"]

                prepared, _ = prepare_price_data(
                    adjusted,
                    as_of_date=as_of,
                    max_age_days=int(max_age),
                    subject_lat=subject_lat,
                    subject_lon=subject_lon,
                    max_distance_km=max_distance,
                    land_type=land_type_filter.strip() or None,
                    apply_outlier_filter=True,
                )
                price_basis = f"reel · {as_of.isoformat()} fiyat düzeyi"
            else:
                prepared, input_rows = prepare_price_data(
                    price_df,
                    as_of_date=as_of,
                    max_age_days=int(max_age),
                    subject_lat=subject_lat,
                    subject_lon=subject_lon,
                    max_distance_km=max_distance,
                    land_type=land_type_filter.strip() or None,
                )

            summary = summarize_comparables(
                prepared,
                input_rows=input_rows,
            )

            a, b, c, d = st.columns(4)
            a.metric("Ham satır", summary.input_rows)
            b.metric("Kullanılan emsal", summary.used_rows)
            c.metric("Medyan TL/m²", f"{summary.median_price_per_m2:,.0f}")
            d.metric("Veri güven etiketi", summary.confidence_label)
            st.caption(f"Fiyat bazı: {price_basis}")

            st.write(
                {
                    "p25_tl_m2": summary.p25_price_per_m2,
                    "p75_tl_m2": summary.p75_price_per_m2,
                    "iqr_tl_m2": summary.iqr_price_per_m2,
                    "dispersion_ratio": summary.dispersion_ratio,
                    "median_age_days": summary.median_age_days,
                    "source_mix": dict(summary.source_mix),
                }
            )
            st.dataframe(
                prepared,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("#### Konu taşınmazın emsal medyanına göre farkı")
            q1, q2 = st.columns(2)
            subject_price = q1.number_input(
                "Konu toplam fiyatı (TL)",
                min_value=1.0,
                value=1000000.0,
                step=50000.0,
            )
            subject_area = q2.number_input(
                "Konu alanı (m²)",
                min_value=1.0,
                value=1000.0,
                step=50.0,
            )
            gap = comparable_gap(
                subject_price_tl=float(subject_price),
                subject_area_m2=float(subject_area),
                comparable_median_price_per_m2=summary.median_price_per_m2,
            )
            x, y, z = st.columns(3)
            x.metric("Konu TL/m²", f"{gap.subject_price_per_m2:,.0f}")
            y.metric("Emsal medyan TL/m²", f"{gap.comparable_median_price_per_m2:,.0f}")
            z.metric("Emsal medyan farkı", f"%{gap.gap_pct:+.1f}")
            st.caption(
                "Pozitif fark, konu fiyatının emsal medyanının altında olduğunu gösterir. "
                "Bu değer otomatik olarak Mispricing Score'a yazılmaz."
            )
        except (
            PriceDataError,
            InflationDataError,
            ValueError,
            pd.errors.ParserError,
        ) as exc:
            st.error(str(exc))


with tab5:
    st.subheader("Planning Intelligence")
    st.caption(
        "Bölgesel ÇDP/WMS kapsamı tek başına imar hakkı değildir. "
        "planning_legal ancak tarih-kesitinde geçerli, FINALIZED ve mekânsal olarak "
        "doğrulanmış UIP/NIP plan kanıtıyla known olur."
    )

    st.markdown(
        "[Resmî e-Plan](https://e-plan.gov.tr/) · "
        "[Askıdaki Planlar](https://e-plan.gov.tr/e-plan/html/acikPlanlar.html?filter=aski) · "
        "[İmar Durumu](https://e-plan.gov.tr/e-plan/html/imarDurumu.html)"
    )

    plan_template = pd.DataFrame(
        [
            {
                "plan_id": "UIP-123456789",
                "title": "Örnek Kesinleşmiş Uygulama İmar Planı",
                "plan_type": "UİP",
                "stage": "kesinleşmiş",
                "source": "e-Plan",
                "source_url": "https://e-plan.gov.tr/",
                "scale_denominator": 1000,
                "published_date": date.today().isoformat(),
                "decision_date": "",
                "effective_date": "",
                "suspension_start": "",
                "suspension_end": "",
                "observed_date": date.today().isoformat(),
                "geometry_verified": False,
                "cell_id": "",
                "province": "",
                "district": "",
                "neighborhood": "",
                "min_lon": "",
                "min_lat": "",
                "max_lon": "",
                "max_lat": "",
                "decision_no": "",
                "pin": "",
                "confidence": 95,
                "note": "Resmî kaynaktan doğrulayın.",
            }
        ]
    )
    st.download_button(
        "Plan Evidence CSV şablonunu indir",
        data=plan_template.to_csv(index=False).encode("utf-8-sig"),
        file_name="land_radar_plan_evidence_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    plan_upload = st.file_uploader(
        "Resmî plan kanıt CSV yükle",
        type=["csv"],
        key="plan_evidence_csv",
    )

    if plan_upload is not None:
        st.dataframe(
            pd.read_csv(plan_upload),
            use_container_width=True,
            hide_index=True,
        )
        plan_upload.seek(0)
        if st.button(
            "Plan CSV'yi registry'ye doğrula ve kaydet",
            use_container_width=True,
            key="save_plan_registry",
        ):
            try:
                processed_dir = Path("data/processed")
                processed_dir.mkdir(parents=True, exist_ok=True)
                upload_path = processed_dir / "plans_uploaded.csv"
                upload_path.write_bytes(plan_upload.getvalue())
                plans = import_plan_csv(
                    upload_path,
                    processed_dir / "plan_registry.json",
                )
                st.success(
                    f"{len(plans)} plan kaydı doğrulandı ve plan_registry.json oluşturuldu."
                )
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "plan_id": p.plan_id,
                                "type": p.plan_type,
                                "stage": p.stage.name,
                                "scale": p.scale_denominator,
                                "published_date": p.published_date,
                                "geometry_verified": p.geometry_verified,
                                "source": p.source,
                            }
                            for p in plans
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            except (PlanImportError, ValueError, FileNotFoundError) as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("#### Top-30 Planning Scan")
    planning_as_of = st.date_input(
        "Planning analiz tarihi",
        value=date.today(),
        key="planning_as_of",
    )
    deep_scan_path = Path("data/output/deep_scan/deep_scan_top30.csv")
    registry_path = Path("data/processed/plan_registry.json")

    if not deep_scan_path.exists():
        st.info(
            "Top-30 dosyası henüz yok. Önce Risk & Funnel / deep scan aşamasını çalıştır."
        )
    else:
        st.caption(
            f"Plan registry: {'hazır' if registry_path.exists() else 'yok — yalnız WMS bağlamı taranacak'}"
        )
        if st.button(
            "Top-30 Planning Scan çalıştır",
            use_container_width=True,
            key="run_planning_scan",
        ):
            try:
                result = run_planning_scan(
                    candidate_csv=deep_scan_path,
                    plan_registry_path=(registry_path if registry_path.exists() else None),
                    output_dir="data/output/planning_scan",
                    as_of_date=planning_as_of,
                )
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Aday", result.candidate_count)
                p2.metric("ÇDP WMS kapsamı", result.wms_covered_count)
                p3.metric("Registry eşleşmesi", result.registry_match_count)
                p4.metric("Planning known", result.planning_known_count)

                planning_df = pd.read_csv(result.output_csv)
                st.dataframe(
                    planning_df,
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Planning Top-30 CSV indir",
                    data=planning_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="planning_top30.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

                if result.planning_known_count == 0:
                    st.warning(
                        "Henüz hiçbir aday FINALIZED + spatially verified UIP/NIP kuralını karşılamıyor. "
                        "ÇDP WMS kapsamı tek başına planning_known yapmaz."
                    )
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))


with tab6:
    st.subheader("Risk & Candidate Funnel")
    st.caption(
        "Bu ekran sihirli Opportunity Score üretmez. GHSL ivmesiyle ilk adayları seçer, "
        "DEM/eğim ve açık hard-veto riskleriyle eleme yapar; eksik veri varsa bunu GAP olarak gösterir."
    )

    rf1, rf2, rf3, rf4 = st.columns(4)
    funnel_cell_km = rf1.select_slider(
        "Funnel hücre boyutu (km)",
        options=[2.0, 5.0, 10.0],
        value=5.0,
        key="funnel_cell_km",
    )
    scan_pool = rf2.select_slider(
        "GHSL tarama havuzu",
        options=[100, 250, 500],
        value=250,
        key="funnel_scan_pool",
    )
    candidate_target = rf3.select_slider(
        "İvme sonrası finalist",
        options=[25, 50, 100],
        value=50,
        key="funnel_candidate_target",
    )
    slope_limit = rf4.slider(
        "P90 eğim üst sınırı (°)",
        min_value=2.0,
        max_value=30.0,
        value=12.0,
        step=0.5,
        key="funnel_slope_limit",
    )

    funnel_ghsl_dir = st.text_input(
        "Funnel GHSL GeoTIFF klasörü",
        value="data/raw/ghsl",
        key="funnel_ghsl_dir",
    )

    st.markdown("#### Opsiyonel resmî risk/hazard GeoJSON")
    hazard_template = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [29.00, 40.00],
                        [29.02, 40.00],
                        [29.02, 40.02],
                        [29.00, 40.02],
                        [29.00, 40.00],
                    ]],
                },
                "properties": {
                    "hazard_id": "official:flood:example",
                    "category": "flood",
                    "severity": "HIGH",
                    "source": "USBS / official export",
                    "observed_date": date.today().isoformat(),
                    "source_url": None,
                    "hard_veto": False,
                    "confidence": 95,
                    "note": "Example only — replace with source-derived classification",
                },
            }
        ],
    }
    st.download_button(
        "Hazard Registry GeoJSON şablonunu indir",
        data=json.dumps(
            hazard_template,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        file_name="land_radar_hazard_registry_template.geojson",
        mime="application/geo+json",
    )
    hazard_upload = st.file_uploader(
        "Hazard Registry GeoJSON yükle (opsiyonel)",
        type=["geojson", "json"],
        key="hazard_registry_upload",
    )

    st.markdown("#### Opsiyonel katalizör Geometry Registry")
    funnel_geometry_upload = st.file_uploader(
        "Catalyst Geometry Registry GeoJSON yükle (opsiyonel)",
        type=["geojson", "json"],
        key="funnel_geometry_registry",
    )

    pf1, pf2 = st.columns(2)
    require_catalyst = pf1.checkbox(
        "Katalizör mesafesi zorunlu olsun",
        value=False,
        key="funnel_require_catalyst",
    )
    catalyst_distance_limit = pf2.slider(
        "Azami katalizör mesafesi (km)",
        min_value=1,
        max_value=50,
        value=20,
        key="funnel_catalyst_distance",
    )

    try:
        funnel_secret_map = st.secrets.to_dict()
    except Exception:
        funnel_secret_map = {}
    funnel_cdse_credentials = resolve_cdse_credentials(funnel_secret_map)
    use_dem = st.checkbox(
        "Copernicus DEM batch taramasını dahil et",
        value=funnel_cdse_credentials is not None,
        disabled=funnel_cdse_credentials is None,
        help=(
            "CDSE OAuth yoksa terrain bilinmiyor olarak kalır; sistem bunu düşük risk saymaz."
        ),
    )
    if funnel_cdse_credentials is None:
        st.info(
            "CDSE OAuth bulunmadı: funnel yine çalışabilir ama terrain_unknown olarak işaretlenir."
        )

    if st.button("Candidate Funnel çalıştır", use_container_width=True):
        try:
            funnel_cells = build_pilot_grid(funnel_cell_km)
            pool_limit = min(int(scan_pool), len(funnel_cells))
            target_limit = min(int(candidate_target), pool_limit)

            urban_pool = scan_grid_ghsl(
                funnel_cells,
                funnel_ghsl_dir,
                limit=pool_limit,
            )
            urban_ranked = rank_accelerating(urban_pool)
            top_urban = urban_ranked[:target_limit]

            cell_by_id = {cell.cell_id: cell for cell in funnel_cells[:pool_limit]}
            selected_cells = [
                cell_by_id[row.cell_id]
                for row in top_urban
                if row.cell_id in cell_by_id
            ]

            terrain_records = []
            if use_dem and funnel_cdse_credentials is not None:
                dem_client = CopernicusProcessClient(
                    funnel_cdse_credentials.client_id,
                    funnel_cdse_credentials.client_secret,
                )
                terrain_records = scan_terrain(
                    selected_cells,
                    dem_client,
                    limit=target_limit,
                    cache_dir="data/cache/terrain",
                    dem_instance="COPERNICUS_90",
                )

            hazard_summaries = []
            hazard_links = []
            if hazard_upload is not None:
                hazard_payload = json.load(hazard_upload)
                hazards = hazards_from_feature_collection(hazard_payload)
                hazard_links = batch_link_hazards(
                    selected_cells,
                    hazards,
                    max_distance_km=20.0,
                )
                hazard_summaries = [
                    summarize_cell_hazards(cell.cell_id, hazard_links)
                    for cell in selected_cells
                ]

            catalyst_links = []
            if funnel_geometry_upload is not None:
                geometry_payload = json.load(funnel_geometry_upload)
                geometry_entries = registry_from_feature_collection(
                    geometry_payload
                )
                catalyst_map = {}

                try:
                    for record in filter_provinces(
                        fetch_osb_list(),
                        ["Sakarya", "Bursa", "Balıkesir", "Çanakkale"],
                    ):
                        catalyst = record_to_catalyst(record)
                        catalyst_map[catalyst.catalyst_id] = catalyst
                except OSBUKProviderError as exc:
                    st.warning(f"OSBÜK status feed alınamadı: {exc}")

                try:
                    for record in fetch_rail_projects():
                        catalyst = rail_record_to_catalyst(record)
                        catalyst_map[catalyst.catalyst_id] = catalyst
                except AYGMRailProviderError as exc:
                    st.warning(f"AYGM status feed alınamadı: {exc}")

                spatial_result = batch_link_catalysts(
                    selected_cells,
                    catalyst_map,
                    geometry_entries,
                    max_distance_km=float(catalyst_distance_limit),
                )
                catalyst_links = list(spatial_result.links)

            policy = CandidatePolicy(
                urban_top_n=target_limit,
                max_p90_slope_deg=float(slope_limit),
                max_catalyst_distance_km=float(catalyst_distance_limit),
                require_catalyst=require_catalyst,
                exclude_hard_veto=True,
            )
            funnel_records = build_candidate_funnel(
                urban_pool,
                terrain_records=terrain_records,
                hazard_summaries=hazard_summaries,
                catalyst_links=catalyst_links,
                policy=policy,
            )
            survivors = surviving_candidates(funnel_records)

            total = len(funnel_records)
            dropped = sum(1 for row in funnel_records if row.status == "DROP")
            gaps = sum(
                1 for row in funnel_records
                if row.status == "PASS_WITH_GAPS"
            )
            clean = sum(1 for row in funnel_records if row.status == "PASS")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("GHSL tarama havuzu", len(urban_pool))
            m2.metric("PASS", clean)
            m3.metric("PASS + veri açığı", gaps)
            m4.metric("DROP", dropped)
            st.caption(
                f"Önce {len(urban_pool)} hücre GHSL ivmesiyle tarandı; "
                f"yalnız ilk {total} finalistte DEM/risk/katalizör derinleştirildi."
            )

            result_rows = [
                {
                    "cell_id": row.cell_id,
                    "lat": row.center_lat,
                    "lon": row.center_lon,
                    "urban_rank": row.urban_rank,
                    "acceleration_pp_year": row.acceleration_pp_per_year,
                    "cagr_2015_2020_pct": row.cagr_2015_2020_pct,
                    "p90_slope_deg": row.p90_slope_deg,
                    "nearest_catalyst_km": row.nearest_catalyst_km,
                    "catalyst_stage_max": row.catalyst_stage_max,
                    "hard_veto": row.hard_veto,
                    "max_hazard_severity": row.max_hazard_severity,
                    "status": row.status,
                    "reasons": ", ".join(row.reasons),
                }
                for row in funnel_records
            ]
            result_df = pd.DataFrame(result_rows)
            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True,
            )

            survivor_df = pd.DataFrame(
                [
                    {
                        "cell_id": row.cell_id,
                        "lat": row.center_lat,
                        "lon": row.center_lon,
                        "status": row.status,
                    }
                    for row in survivors
                ]
            )
            if not survivor_df.empty:
                st.markdown("#### Hayatta kalan araştırma adayları")
                st.map(
                    survivor_df,
                    latitude="lat",
                    longitude="lon",
                )

            st.download_button(
                "Candidate Funnel sonucunu CSV indir",
                data=result_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="land_radar_candidate_funnel.csv",
                mime="text/csv",
                use_container_width=True,
            )

            if hazard_links:
                st.caption(
                    f"Hazard link sayısı: {len(hazard_links)}. Hard-veto yalnız hücreyle kesişen "
                    "ve kaynak dosyada hard_veto=true olan bulgulardan gelir."
                )
            if not terrain_records:
                st.warning(
                    "DEM batch çalışmadı/kullanılmadı. terrain_unknown hücreler düşük eğimli kabul edilmedi."
                )
            if not catalyst_links:
                st.warning(
                    "Doğrulanmış katalizör geometry registry bağlantısı yok. "
                    "Katalizör verisi eksik olarak tutuldu."
                )

        except (
            GHSLProviderError,
            CopernicusDEMError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            st.error(str(exc))


with tab7:
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

with tab8:
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

    st.divider()
    st.markdown("#### OSBÜK pilot durum akışı")
    st.caption(
        "Bu aşama yalnız OSB'nin yayımlanan durumunu ve katalizör aşamasını gösterir. "
        "Koordinat/geometri olmadığı için seçili hücreye mesafe hesabı yapılmaz."
    )
    pilot_provinces = ["Sakarya", "Bursa", "Balıkesir", "Çanakkale"]
    if st.button("Pilot illerin OSB durumlarını getir", use_container_width=True):
        try:
            osb_records = filter_provinces(fetch_osb_list(), pilot_provinces)
            rows = []
            for record in osb_records:
                catalyst = record_to_catalyst(record)
                rows.append(
                    {
                        "province": record.province,
                        "osb": record.name,
                        "raw_status": record.status,
                        "stage": int(catalyst.stage),
                        "stage_label": STAGE_LABELS[catalyst.stage],
                        "evidence_confidence": catalyst.evidence_confidence,
                        "address": record.address,
                    }
                )
            st.success(f"{len(rows)} OSB kaydı alındı.")
            st.dataframe(rows, use_container_width=True, hide_index=True)
        except OSBUKProviderError as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("#### AYGM / UAB demiryolu katalizör akışı")
    st.caption(
        "AYGM'nin resmî devam eden / tamamlanan / planlanan proje gruplarını "
        "Catalyst State Machine'e çevirir. Güzergâh geometrisi henüz bağlanmadığı "
        "için hücre mesafesi veya etki yarıçapı hesaplanmaz."
    )
    rail_keywords = ["bandırma", "bursa", "osmaneli", "sakarya"]
    if st.button("Pilot koridor demiryolu projelerini getir", use_container_width=True):
        try:
            rail_records = filter_project_keywords(
                fetch_rail_projects(),
                rail_keywords,
            )
            rail_rows = []
            for record in rail_records:
                catalyst = rail_record_to_catalyst(record)
                rail_rows.append(
                    {
                        "project": record.name,
                        "official_group": record.status_group,
                        "stage": int(catalyst.stage),
                        "stage_label": STAGE_LABELS[catalyst.stage],
                        "evidence_confidence": catalyst.evidence_confidence,
                        "source": record.source_url,
                    }
                )
            st.success(f"{len(rail_rows)} demiryolu proje kaydı eşleşti.")
            st.dataframe(rail_rows, use_container_width=True, hide_index=True)
        except AYGMRailProviderError as exc:
            st.error(str(exc))
