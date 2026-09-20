/**
 * Landslide Early-Warning System (LEWS) - Interactive GIS Command Center
 * SIH PS 26001 - Production Build
 */

// Global State
let map;
let basemaps = {};
let currentBasemap = 'dark';
let stationLayerGroup;
let historicalLayerGroup;
let suscepLayerGroup;
let inspectMarker;

let stationsData = [];
let historicalLandslides = [];
let replayEvents = [];
let activeReplayEvent = null;
let replayTimer = null;
let isReplayPlaying = false;
let replayChartInstance = null;
let rocChartInstance = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) lucide.createIcons();
  initTabs();
  initMap();
  await loadInitialData();
  refreshDataCenter();
});

// 1. Tab Navigation
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab-btn');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      const targetTab = document.getElementById(tabId);
      if (targetTab) {
        targetTab.classList.add('active');
        if (tabId === 'tab-map' && map) {
          setTimeout(() => map.invalidateSize(), 200);
        } else if (tabId === 'tab-datacenter') {
          refreshDataCenter();
        }
      }
    });
  });
}

// 2. Leaflet Map Initialization
function initMap() {
  map = L.map('map', {
    center: [27.42, 88.52],
    zoom: 10,
    zoomControl: true
  });

  // Basemaps (Standard open providers with HTTPS)
  basemaps.dark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; CartoDB, OpenStreetMap contributors',
    subdomains: 'abcd',
    maxZoom: 18
  });

  basemaps.sat = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
    attribution: '&copy; Google Satellite Imagery',
    maxZoom: 20
  });

  basemaps.topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenTopoMap contributors',
    maxZoom: 17
  });

  basemaps.dark.addTo(map);

  // Layer Groups
  suscepLayerGroup = L.layerGroup().addTo(map);
  historicalLayerGroup = L.layerGroup().addTo(map);
  stationLayerGroup = L.layerGroup().addTo(map);

  renderSusceptibilityPolygons();

  map.on('click', async (e) => {
    const { lat, lng } = e.latlng;
    inspectCoordinate(lat, lng);
  });

  setTimeout(() => {
    if (map) map.invalidateSize();
  }, 250);

  window.addEventListener('resize', () => {
    if (map) map.invalidateSize();
  });
}

function switchBasemap(type) {
  ['dark', 'sat', 'topo'].forEach(t => {
    if (map.hasLayer(basemaps[t])) map.removeLayer(basemaps[t]);
    const btn = document.getElementById(`btn-basemap-${t}`);
    if (btn) btn.classList.remove('active');
  });

  basemaps[type].addTo(map);
  const activeBtn = document.getElementById(`btn-basemap-${type}`);
  if (activeBtn) activeBtn.classList.add('active');
  currentBasemap = type;
}

function toggleSusceptibilityLayer() {
  const btn = document.getElementById('btn-toggle-suscep');
  if (map.hasLayer(suscepLayerGroup)) {
    map.removeLayer(suscepLayerGroup);
    btn.classList.remove('active');
  } else {
    map.addLayer(suscepLayerGroup);
    btn.classList.add('active');
  }
}

function toggleHistoricalLayer() {
  const btn = document.getElementById('btn-toggle-historical');
  if (map.hasLayer(historicalLayerGroup)) {
    map.removeLayer(historicalLayerGroup);
    btn.classList.remove('active');
  } else {
    map.addLayer(historicalLayerGroup);
    btn.classList.add('active');
  }
}

function toggleStationsLayer() {
  const btn = document.getElementById('btn-toggle-stations');
  if (map.hasLayer(stationLayerGroup)) {
    map.removeLayer(stationLayerGroup);
    btn.classList.remove('active');
  } else {
    map.addLayer(stationLayerGroup);
    btn.classList.add('active');
  }
}

let suscepGeoJsonLayer = null;

// 3. Susceptibility Polygons (Interactive GeoJSON Data Layer)
async function renderSusceptibilityPolygons() {
  suscepLayerGroup.clearLayers();

  try {
    const res = await fetch('/api/susceptibility');
    if (!res.ok) return;
    const geojson = await res.json();

    suscepGeoJsonLayer = L.geoJSON(geojson, {
      style: function (feature) {
        const p = feature.properties || {};
        let color = '#f59e0b';
        if (p.susceptibility_class === 'High') color = '#ef4444';
        else if (p.susceptibility_class === 'Low') color = '#10b981';

        return {
          color: color,
          weight: 2,
          opacity: 0.85,
          fillColor: color,
          fillOpacity: p.susceptibility_class === 'High' ? 0.30 : 0.20,
          dashArray: '3, 4'
        };
      },
      onEachFeature: function (feature, layer) {
        const p = feature.properties || {};
        const center = layer.getBounds().getCenter();

        layer.on({
          mouseover: function (e) {
            const l = e.target;
            l.setStyle({
              weight: 3.5,
              fillOpacity: 0.50,
              dashArray: ''
            });
            if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
              l.bringToFront();
            }
          },
          mouseout: function (e) {
            if (suscepGeoJsonLayer) suscepGeoJsonLayer.resetStyle(e.target);
          },
          click: function (e) {
            inspectCoordinate(center.lat, center.lng);
          }
        });

        layer.bindTooltip(`
          <strong>${p.name}</strong><br>
          District: ${p.district} | Class: <span style="color:${p.color || '#f59e0b'}; font-weight:700;">${p.susceptibility_class}</span><br>
          Mean Slope: ${p.mean_slope_deg}° • Elev: ${p.elevation_range_m}m
        `, { sticky: true });

        layer.bindPopup(`
          <div style="font-family:sans-serif; min-width:230px; color:#111;">
            <div style="font-size:10px; font-weight:700; color:${p.color || '#ef4444'}; text-transform:uppercase;">GSI NLSM Susceptibility Zone (${p.zone_id})</div>
            <h4 style="margin:2px 0 6px; font-size:13px;">${p.name}</h4>
            <div style="font-size:11px; margin-bottom:2px;">District: <strong>${p.district}</strong> (${p.susceptibility_class} Hazard)</div>
            <div style="font-size:11px; margin-bottom:2px;">Critical Corridor: <strong>${p.critical_corridor}</strong></div>
            <div style="font-size:11px; margin-bottom:2px;">Slope / Elev: <strong>${p.mean_slope_deg}°</strong> | <strong>${p.elevation_range_m}m</strong></div>
            <div style="font-size:11px; margin-bottom:4px;">Lithology: <em>${p.lithology}</em></div>
            <div style="font-size:10px; color:#555; background:#f1f5f9; padding:4px; border-radius:4px; margin-top:4px;">
              ${p.geomorphology}
            </div>
            <button onclick="inspectCoordinate(${center.lat}, ${center.lng})" style="margin-top:8px; width:100%; background:#1e293b; color:#fff; border:none; padding:5px 8px; border-radius:4px; cursor:pointer; font-size:11px;">
              Inspect Live Sensor Telemetry
            </button>
          </div>
        `);
      }
    }).addTo(suscepLayerGroup);
  } catch (err) {
    console.error("Error loading susceptibility GeoJSON:", err);
  }
}

// 4. Data Loading
async function loadInitialData() {
  // Immediately inspect initial central coordinate (Gangtok Capital Corridor)
  inspectCoordinate(27.3389, 88.6065);

  // Load all subsystems concurrently with fault-isolation
  const promises = [
    fetch('/api/stations')
      .then(res => res.ok ? res.json() : [])
      .then(data => {
        stationsData = data;
        populateStationSelector(stationsData);
        renderStationMarkers(stationsData);
      })
      .catch(e => console.error("Error loading stations:", e)),

    fetch('/api/landslides')
      .then(res => res.ok ? res.json() : [])
      .then(data => {
        historicalLandslides = data;
        renderHistoricalLandslides(historicalLandslides);
      })
      .catch(e => console.error("Error loading landslides:", e)),

    loadActiveAlerts().catch(e => console.error("Error loading alerts:", e)),

    fetch('/api/replay')
      .then(res => res.ok ? res.json() : [])
      .then(data => {
        replayEvents = data;
        populateReplaySelector(replayEvents);
      })
      .catch(e => console.error("Error loading replay:", e)),

    loadValidationData().catch(e => console.error("Error loading validation analytics:", e))
  ];

  await Promise.allSettled(promises);
}

function renderStationMarkers(stations) {
  stationLayerGroup.clearLayers();

  stations.forEach(stn => {
    const risk = stn.risk_assessment;
    const color = risk.badge_color;

    const marker = L.circleMarker([stn.lat, stn.lon], {
      radius: 10,
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9
    });

    marker.bindPopup(`
      <div style="font-family:sans-serif; min-width:210px; color:#111;">
        <h4 style="margin:0 0 4px; color:${color}; font-weight:700;">${stn.name}</h4>
        <div style="font-size:12px; margin-bottom:4px;">District: <strong>${stn.district}</strong></div>
        <div style="font-size:12px;">Slope: <strong>${risk.factors.slope_deg}°</strong> | Elev: <strong>${risk.factors.elevation_m}m</strong></div>
        <div style="font-size:12px; margin-top:4px;">
          Hazard Index: <strong>${risk.risk_score}</strong><br>
          ML Landslide Prob: <strong style="color:${color};">${(risk.ml_probability * 100).toFixed(1)}%</strong>
        </div>
        <div style="font-size:11px; color:#555; margin-top:4px;">24h Rain: ${risk.factors.rain_24h}mm</div>
        <button onclick="inspectCoordinate(${stn.lat}, ${stn.lon})" style="margin-top:8px; width:100%; background:#1e293b; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:11px;">
          Inspect Node Details
        </button>
      </div>
    `);

    marker.on('click', () => {
      inspectCoordinate(stn.lat, stn.lon);
    });

    marker.addTo(stationLayerGroup);
  });
}

function renderHistoricalLandslides(events) {
  historicalLayerGroup.clearLayers();

  const customIcon = L.divIcon({
    className: 'custom-landslide-pin',
    html: '<div style="background:#dc2626; color:#fff; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; border:2px solid #fff; box-shadow:0 2px 6px rgba(0,0,0,0.5);">📍</div>',
    iconSize: [22, 22],
    iconAnchor: [11, 11]
  });

  events.forEach(ev => {
    const marker = L.marker([ev.lat, ev.lon], { icon: customIcon });
    marker.bindPopup(`
      <div style="font-family:sans-serif; min-width:210px; color:#111;">
        <div style="font-size:10px; font-weight:700; color:#dc2626; text-transform:uppercase;">GSI Field-Validated Record (${ev.year || ''})</div>
        <h4 style="margin:2px 0 6px; font-size:13px;">${ev.location_name}</h4>
        <div style="font-size:11px; margin-bottom:2px;">Date: <strong>${ev.event_date}</strong></div>
        <div style="font-size:11px; margin-bottom:2px;">Type: <strong>${ev.type}</strong></div>
        <div style="font-size:11px; margin-bottom:2px;">Trigger Rain (24h): <strong>${ev.trigger_rain_24h_mm} mm</strong></div>
        <div style="font-size:11px; margin-bottom:4px;">Slope: <strong>${ev.slope_deg}°</strong> (${ev.susceptibility} Zone)</div>
        <div style="font-size:11px; color:#444; background:#f1f5f9; padding:4px; border-radius:4px; margin-top:4px;">
          ${ev.damage_summary}
        </div>
      </div>
    `);
    marker.addTo(historicalLayerGroup);
  });
}

function populateStationSelector(stations) {
  const select = document.getElementById('station-select');
  select.innerHTML = '';
  stations.forEach((stn, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `${stn.name} (${stn.district}) - ${stn.risk_assessment.risk_level}`;
    select.appendChild(opt);
  });
}

function onStationSelectChange(index) {
  const stn = stationsData[index];
  if (stn) {
    inspectCoordinate(stn.lat, stn.lon);
    map.flyTo([stn.lat, stn.lon], 12);
  }
}

// 5. Inspect Coordinate
async function inspectCoordinate(lat, lon) {
  if (inspectMarker) map.removeLayer(inspectMarker);

  inspectMarker = L.circleMarker([lat, lon], {
    radius: 14,
    fillColor: 'transparent',
    color: '#06b6d4',
    weight: 3,
    dashArray: '3, 3'
  }).addTo(map);

  try {
    const res = await fetch(`/api/risk?lat=${lat}&lon=${lon}`);
    const risk = await res.json();
    updateInspectorDisplay(risk);
  } catch (e) {
    console.error("Failed to query risk at coordinate:", e);
  }
}

function updateInspectorDisplay(risk) {
  document.getElementById('inspector-coords').textContent = `${risk.lat.toFixed(4)}° N, ${risk.lon.toFixed(4)}° E`;
  
  // 5. Compound Risk (Primary Gauge)
  const compoundScoreEl = document.getElementById('inspector-compound-score');
  if (compoundScoreEl) {
    compoundScoreEl.textContent = (risk.compound_risk !== undefined) ? risk.compound_risk.toFixed(2) : (risk.risk_score.toFixed(2));
    compoundScoreEl.style.color = risk.badge_color;
  }

  const levelEl = document.getElementById('inspector-level');
  levelEl.textContent = `${risk.risk_level} HAZARD`;
  levelEl.style.backgroundColor = `${risk.badge_color}33`;
  levelEl.style.color = risk.badge_color;

  // 3. ML Prediction & 4. Physics Hazard
  const mlProbEl = document.getElementById('inspector-ml-prob');
  if (mlProbEl) mlProbEl.textContent = `${(risk.ml_probability * 100).toFixed(1)}%`;
  
  const scoreEl = document.getElementById('inspector-score');
  if (scoreEl) {
    scoreEl.textContent = risk.risk_score.toFixed(2);
    scoreEl.style.color = risk.risk_score >= 0.65 ? '#ef4444' : (risk.risk_score >= 0.45 ? '#fbbf24' : '#10b981');
  }

  // 1. Static Susceptibility
  const trace = risk.prediction_trace || {};
  const staticSus = trace.static_susceptibility || (risk.susceptibility_data || {});
  const isInside = staticSus.is_inside_mapped_polygon === true;

  const suscepStatusEl = document.getElementById('inspector-suscep-status');
  if (suscepStatusEl) {
    suscepStatusEl.textContent = isInside ? 'Inside Mapped GSI NLSM Zone' : 'Outside Mapped GSI Coverage';
    suscepStatusEl.style.color = isInside ? '#38bdf8' : '#a78bfa';
    suscepStatusEl.style.background = isInside ? 'rgba(56,189,248,0.15)' : 'rgba(167,139,250,0.15)';
  }

  const suscepClassEl = document.getElementById('inspector-suscep-class');
  if (suscepClassEl) {
    const sClass = risk.factors.susceptibility || (isInside ? 'Moderate' : 'Low');
    const sFactor = risk.factors.suscep_factor !== undefined ? risk.factors.suscep_factor : (isInside ? 0.5 : 0.1);
    suscepClassEl.textContent = `${sClass} (${sFactor})`;
    suscepClassEl.style.color = sClass === 'High' ? '#ef4444' : (sClass === 'Moderate' ? '#fbbf24' : '#10b981');
  }

  const suscepSourceEl = document.getElementById('inspector-suscep-source');
  if (suscepSourceEl) {
    suscepSourceEl.textContent = isInside ? (staticSus.source || 'GSI NLSM 1:50k Corridor') : 'SRTM 30m Slope Baseline';
  }

  // 2. Dynamic Conditions & Terrain
  document.getElementById('factor-rain24').textContent = `${risk.factors.rain_24h} / ${risk.factors.rain_48h || 0} mm`;
  document.getElementById('factor-slope').textContent = `${risk.factors.slope_deg}°`;
  document.getElementById('factor-rain7d').textContent = `${risk.factors.rain_7d} mm`;
  document.getElementById('factor-soil').textContent = `${risk.factors.soil_0_10cm} m³/m³`;

  const meta = risk.telemetry_metadata || {};
  document.getElementById('inspector-data-provenance').textContent = 
    `Telemetry: ${meta.weather_source || 'Open-Meteo'} (${meta.weather_timestamp || 'Live'}) • DEM: ${meta.dem_source || 'SRTM 30m'} • Model: ${meta.model_version || 'XGB-v3.0'}`;

  // 6. Scientific Synthesis Note
  document.getElementById('inspector-explanation').textContent = risk.note || 'No immediate anomalies observed.';

  const advContainer = document.getElementById('inspector-advisories');
  advContainer.innerHTML = '';
  (risk.emergency_advisories || []).forEach(adv => {
    const div = document.createElement('div');
    div.className = 'advisory-item';
    if (risk.risk_level === 'LOW') {
      div.style.borderColor = '#10b981';
      div.style.background = 'rgba(16,185,129,0.1)';
      div.style.color = '#a7f3d0';
    }
    div.textContent = adv;
    advContainer.appendChild(div);
  });

  // Populate Data Center 5-Stage Trace
  const s1 = trace.stage_1_raw_telemetry || {};
  const s2 = trace.stage_2_normalized_features || {};
  const s3 = trace.stage_3_ml_feature_vector || {};
  const s4 = trace.stage_4_model_outputs || {};
  const s5 = trace.stage_5_final_decision || {};

  const el1 = document.getElementById('trace-stage-1');
  if (el1) el1.innerHTML = `Lat/Lon: ${risk.lat.toFixed(4)}, ${risk.lon.toFixed(4)}<br>Rain 24h: ${s1.rain_24h_mm ?? '--'}mm | 7d: ${s1.rain_7d_mm ?? '--'}mm<br>Source: ${s1.weather_source ?? 'N/A'}`;

  const el2 = document.getElementById('trace-stage-2');
  if (el2) el2.innerHTML = `Norm Rain 24h: ${s2.norm_rain_24h ?? '--'}<br>Norm Slope: ${s2.norm_slope ?? '--'}<br>Norm Soil: ${s2.norm_soil ?? '--'}`;

  const el3 = document.getElementById('trace-stage-3');
  if (el3 && s3.feature_values) el3.innerHTML = `Vector [1x10]:<br>[${s3.feature_values.join(', ')}]`;

  const el4 = document.getElementById('trace-stage-4');
  if (el4) el4.innerHTML = `Model: ${s4.model_name ?? 'XGBoost'}<br>ML Prob: ${s4.ml_probability !== undefined ? (s4.ml_probability * 100).toFixed(1) + '%' : '--'}<br>GSI Breached: ${s4.gsi_id_power_law_breached ? 'YES (OVERRIDE)' : 'NO'}`;

  const el5 = document.getElementById('trace-stage-5');
  if (el5) el5.innerHTML = `Compound Risk: ${s5.compound_risk ?? '--'}<br>Hazard Level: <strong style="color:${s5.badge_color}">${s5.risk_level ?? '--'}</strong><br>Advisories: ${s5.action_advisories_count ?? 0} dispatched`;

  // Raw JSON display
  const dcTrace = document.getElementById('dc-decision-trace');
  if (dcTrace) {
    dcTrace.textContent = JSON.stringify(risk, null, 2);
  }

  // Update Weather Data Center cards with clicked point weather if available
  if (risk.weather_data && risk.weather_data.status !== 'UNAVAILABLE') {
    const wd = risk.weather_data;
    const wRainCur = document.getElementById('dc-w-rain-cur');
    if (wRainCur) wRainCur.textContent = `${wd.rain_intensity_mmh ?? 0.0} mm/h`;
    const wWindows = document.getElementById('dc-w-rain-windows');
    if (wWindows) wWindows.textContent = `6h: ${wd.rain_6h ?? 0}mm • 24h: ${wd.rain_24h ?? 0}mm • 48h: ${wd.rain_48h ?? 0}mm • 7d: ${wd.rain_7d ?? 0}mm`;
    const wTemp = document.getElementById('dc-w-temp');
    if (wTemp) wTemp.textContent = wd.current_temperature_c !== undefined ? `${wd.current_temperature_c} °C` : '-- °C';
    const wHumid = document.getElementById('dc-w-humid');
    if (wHumid) wHumid.textContent = `Relative Humidity: ${wd.current_relative_humidity_pct ?? '--'}% • Wind: ${wd.current_wind_speed_kmh ?? '--'} km/h`;
    const wFc = document.getElementById('dc-w-forecast24');
    if (wFc) wFc.textContent = `${wd.forecast_24h ?? 0.0} mm`;
    const wStatus = document.getElementById('dc-w-status');
    if (wStatus) {
      wStatus.textContent = wd.status || 'LIVE';
      wStatus.style.color = wd.status === 'LIVE' ? '#10b981' : (wd.status === 'CACHED' ? '#f59e0b' : '#ef4444');
    }
    const wFetch = document.getElementById('dc-w-fetchtime');
    if (wFetch) wFetch.textContent = `Fetched: ${wd.last_fetched_iso || 'Live'} (Lat: ${risk.lat.toFixed(4)}, Lon: ${risk.lon.toFixed(4)})`;

    // Soil moisture
    if (wd.soil_layers) {
      const s01 = document.getElementById('dc-soil-0-1');
      if (s01) s01.textContent = `${wd.soil_layers['0_1cm'] ?? '--'} m³/m³`;
      const s13 = document.getElementById('dc-soil-1-3');
      if (s13) s13.textContent = `${wd.soil_layers['1_3cm'] ?? '--'} m³/m³`;
      const s39 = document.getElementById('dc-soil-3-9');
      if (s39) s39.textContent = `${wd.soil_layers['3_9cm'] ?? '--'} m³/m³`;
      const s927 = document.getElementById('dc-soil-9-27');
      if (s927) s927.textContent = `${wd.soil_layers['9_27cm'] ?? '--'} m³/m³`;
    }
    const sAgg0 = document.getElementById('dc-soil-agg-0-10');
    if (sAgg0) sAgg0.textContent = `${wd.soil_0_10cm ?? '--'} m³/m³`;
    const sAgg10 = document.getElementById('dc-soil-agg-10-40');
    if (sAgg10) sAgg10.textContent = `${wd.soil_10_40cm ?? '--'} m³/m³`;
  }
}

// 6. Historical Replay
function populateReplaySelector(events) {
  const select = document.getElementById('replay-event-select');
  select.innerHTML = '';
  events.forEach(ev => {
    const opt = document.createElement('option');
    opt.value = ev.event_id;
    opt.textContent = `${ev.title} (${ev.district})`;
    select.appendChild(opt);
  });

  if (events.length > 0) {
    loadReplayEvent(events[0].event_id);
  }
}

function loadReplayEvent(eventId) {
  resetReplay();
  activeReplayEvent = replayEvents.find(e => e.event_id === eventId);
  if (!activeReplayEvent) return;

  document.getElementById('replay-lead-time-stat').textContent = `${activeReplayEvent.calculated_lead_time_hours} Hours`;

  const labelsContainer = document.getElementById('replay-timeline-labels');
  labelsContainer.innerHTML = '';
  const slider = document.getElementById('replay-slider');
  slider.max = activeReplayEvent.timeline.length - 1;
  slider.value = 0;

  activeReplayEvent.timeline.forEach(step => {
    const span = document.createElement('span');
    span.textContent = step.time_display.split(' ')[0];
    labelsContainer.appendChild(span);
  });

  renderReplayChart(activeReplayEvent);
  renderReplayStep(0);

  if (window.lucide) lucide.createIcons();
}

function onReplaySliderChange(stepIdx) {
  renderReplayStep(parseInt(stepIdx));
}

function renderReplayStep(stepIdx) {
  if (!activeReplayEvent) return;
  const step = activeReplayEvent.timeline[stepIdx];
  if (!step) return;

  document.getElementById('replay-step-time').textContent = step.time_display;
  
  const levelEl = document.getElementById('replay-metric-level');
  levelEl.textContent = step.risk_level;
  let color = '#10b981';
  if (step.risk_level.includes('HIGH') || step.risk_level.includes('CRITICAL')) color = '#ef4444';
  else if (step.risk_level.includes('MODERATE')) color = '#f59e0b';
  levelEl.style.color = color;

  document.getElementById('replay-metric-score').textContent = `Hazard Score: ${step.risk_score.toFixed(2)}`;
  document.getElementById('replay-metric-rain-int').textContent = `${step.rain_intensity_mmh} mm/h`;
  document.getElementById('replay-metric-rain-24h').textContent = `${step.rain_24h_mm} mm`;
  document.getElementById('replay-metric-soil').textContent = `${step.soil_moisture_0_10cm} m³/m³`;

  const statusBox = document.getElementById('replay-status-box');
  statusBox.textContent = step.status_message;
  if (step.risk_level.includes('HIGH') || step.risk_level.includes('CRITICAL')) {
    statusBox.style.borderColor = '#ef4444';
    statusBox.style.background = 'rgba(239, 68, 68, 0.15)';
  } else {
    statusBox.style.borderColor = 'var(--border-color)';
    statusBox.style.background = 'var(--bg-secondary)';
  }
}

function toggleReplayPlay() {
  if (isReplayPlaying) {
    pauseReplay();
  } else {
    startReplay();
  }
}

function startReplay() {
  isReplayPlaying = true;
  const btn = document.getElementById('btn-replay-play');
  btn.innerHTML = '<i data-lucide="pause" style="width:16px; height:16px;"></i> <span>Pause Timeline</span>';
  if (window.lucide) lucide.createIcons();

  const slider = document.getElementById('replay-slider');
  replayTimer = setInterval(() => {
    let cur = parseInt(slider.value);
    if (cur < activeReplayEvent.timeline.length - 1) {
      cur += 1;
      slider.value = cur;
      renderReplayStep(cur);
    } else {
      pauseReplay();
    }
  }, 1600);
}

function pauseReplay() {
  isReplayPlaying = false;
  if (replayTimer) clearInterval(replayTimer);
  const btn = document.getElementById('btn-replay-play');
  btn.innerHTML = '<i data-lucide="play" style="width:16px; height:16px;"></i> <span>Play Timeline</span>';
  if (window.lucide) lucide.createIcons();
}

function resetReplay() {
  pauseReplay();
  const slider = document.getElementById('replay-slider');
  if (slider) {
    slider.value = 0;
    renderReplayStep(0);
  }
}

function renderReplayChart(eventData) {
  const ctx = document.getElementById('replayChart').getContext('2d');
  if (replayChartInstance) replayChartInstance.destroy();

  const labels = eventData.timeline.map(t => t.time_display.split(' (')[0]);
  const rainData = eventData.timeline.map(t => t.rain_24h_mm);
  const riskData = eventData.timeline.map(t => t.risk_score * 100);

  replayChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: '24h Rainfall (mm)',
          data: rainData,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          yAxisID: 'yRain',
          tension: 0.3,
          fill: true
        },
        {
          label: 'Hazard Index (0-100%)',
          data: riskData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          yAxisID: 'yRisk',
          tension: 0.3,
          borderWidth: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        yRain: {
          type: 'linear',
          position: 'left',
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        },
        yRisk: {
          type: 'linear',
          position: 'right',
          max: 100,
          min: 0,
          grid: { drawOnChartArea: false },
          ticks: { color: '#ef4444' }
        },
        x: {
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: { labels: { color: '#f8fafc' } }
      }
    }
  });
}

// 7. What-If Simulation
function onSimSliderChange(val) {
  document.getElementById('sim-boost-val').textContent = `+${val}%`;
}

async function runSimulation() {
  const boostPct = parseFloat(document.getElementById('sim-slider').value);
  const summaryEl = document.getElementById('sim-result-summary');
  summaryEl.textContent = 'Simulating regional slope matrix...';

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rain_boost_pct: boostPct })
    });
    const data = await res.json();
    summaryEl.textContent = data.summary;

    renderSimStationCards(data.station_results);
  } catch (err) {
    summaryEl.textContent = 'Simulation failed to run.';
  }
}

function renderSimStationCards(results) {
  const grid = document.getElementById('sim-stations-grid');
  grid.innerHTML = '';

  results.forEach(res => {
    const card = document.createElement('div');
    card.className = 'station-card';

    let badgeColor = '#10b981';
    if (res.simulated_level === 'CRITICAL' || res.simulated_level === 'HIGH') badgeColor = '#ef4444';
    else if (res.simulated_level === 'MODERATE') badgeColor = '#f59e0b';

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <h4 style="font-size:0.92rem; font-weight:700;">${res.station_name}</h4>
          <div style="font-size:0.75rem; color:var(--text-muted);">${res.district} • Slope: ${res.slope_deg}°</div>
        </div>
        <span style="background:${badgeColor}22; color:${badgeColor}; border:1px solid ${badgeColor}; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700;">
          ${res.simulated_level}
        </span>
      </div>
      <div style="margin-top:12px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-size:0.7rem; color:var(--text-muted);">Hazard Index</div>
          <div class="mono" style="font-size:1.2rem; font-weight:800; color:${badgeColor};">${res.simulated_score.toFixed(2)}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.7rem; color:var(--text-muted);">ML Landslide Prob</div>
          <div class="mono" style="font-size:1.2rem; font-weight:800; color:var(--accent-cyan);">
            ${(res.simulated_ml_prob * 100).toFixed(1)}%
          </div>
        </div>
      </div>
      <div style="font-size:0.75rem; color:#cbd5e1; margin-top:8px; line-height:1.3;">
        ${res.simulated_note}
      </div>
    `;
    grid.appendChild(card);
  });
}

// 8. Dynamic Validation Data & Charts Rendering
async function loadValidationData() {
  try {
    const res = await fetch('/api/validation');
    if (!res.ok) throw new Error("Validation data not available");
    const val = await res.json();

    // 1. Populate Evaluation Period
    if (document.getElementById('val-eval-period')) {
      document.getElementById('val-eval-period').textContent = `${val.test_period} (Train: ${val.train_period})`;
    }

    // 2. Populate KPI Cards
    const metrics = val.metrics || {};
    document.getElementById('val-metric-precision').textContent = `${metrics.precision_pct}%`;
    document.getElementById('val-metric-recall').textContent = `${metrics.recall_pct}%`;
    document.getElementById('val-metric-f1').textContent = `${metrics.f1_score_pct}%`;
    document.getElementById('val-metric-leadtime').textContent = `${metrics.median_warning_lead_time_hours} hrs`;
    document.getElementById('val-metric-auc').textContent = metrics.roc_auc ? metrics.roc_auc.toFixed(3) : '0.98';

    // 3. Populate Confusion Matrix Table
    const cm = val.confusion_matrix || {};
    document.getElementById('val-total-samples').textContent = val.total_test_samples || (cm.tp + cm.fp + cm.fn + cm.tn);
    document.getElementById('cm-tp').textContent = `TP: ${cm.tp}`;
    document.getElementById('cm-fp').textContent = `FP: ${cm.fp} (${metrics.false_alarm_rate_pct || 0}% False Alarm)`;
    document.getElementById('cm-fn').textContent = `FN: ${cm.fn} (Missed)`;
    document.getElementById('cm-tn').textContent = `TN: ${cm.tn}`;

    // 4. Populate Model Comparison Table Body
    const tbody = document.getElementById('model-comparison-tbody');
    if (tbody && val.models_comparison) {
      tbody.innerHTML = '';
      val.models_comparison.forEach(m => {
        const tr = document.createElement('tr');
        if (m.model.includes('Random Forest')) {
          tr.style.background = 'rgba(59,130,246,0.12)';
          tr.style.fontWeight = '700';
        }
        tr.innerHTML = `
          <td style="text-align:left;">${m.model}</td>
          <td>${m.precision}</td>
          <td>${m.recall}</td>
          <td>${m.f1}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    // 5. Populate Feature Importance Bars
    const list = document.getElementById('feature-importance-list');
    list.innerHTML = '';
    (val.feature_importance_ranking || []).forEach(f => {
      const row = document.createElement('div');
      row.style.marginBottom = '10px';
      row.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:4px;">
          <span>${f.feature}</span>
          <span class="mono" style="color:var(--accent-cyan); font-weight:700;">${f.percentage}%</span>
        </div>
        <div style="background:var(--bg-card); height:8px; border-radius:4px; overflow:hidden;">
          <div style="background:var(--color-blue); width:${f.percentage}%; height:100%;"></div>
        </div>
      `;
      list.appendChild(row);
    });

    // 6. Populate Dynamic ROC Curve
    const ctx = document.getElementById('rocChart').getContext('2d');
    if (rocChartInstance) rocChartInstance.destroy();

    const rocData = (val.roc_curve_samples || []).map(p => ({ x: p.false_positive_rate, y: p.true_positive_rate }));

    rocChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        datasets: [
          {
            label: `Random Forest (AUC = ${metrics.roc_auc || 0.98})`,
            data: rocData,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            fill: true,
            tension: 0.2
          },
          {
            label: 'Random Baseline (AUC = 0.50)',
            data: [{x:0, y:0}, {x:1, y:1}],
            borderColor: '#64748b',
            borderDash: [5, 5],
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'linear',
            min: 0,
            max: 1,
            title: { display: true, text: 'False Positive Rate', color: '#94a3b8' },
            ticks: { color: '#94a3b8' }
          },
          y: {
            min: 0,
            max: 1,
            title: { display: true, text: 'True Positive Rate (Recall)', color: '#94a3b8' },
            ticks: { color: '#94a3b8' }
          }
        },
        plugins: {
          legend: { labels: { color: '#f8fafc' } }
        }
      }
    });

  } catch (err) {
    console.error("Error loading validation analytics:", err);
  }
}

// 9. Alerts & Reports
async function loadActiveAlerts() {
  try {
    const alertRes = await fetch('/api/alerts');
    const alerts = await alertRes.json();
    document.getElementById('active-alert-count').textContent = alerts.length;

    const alertCont = document.getElementById('alerts-list-container');
    alertCont.innerHTML = '';
    alerts.forEach(a => {
      const card = document.createElement('div');
      card.className = 'station-card';
      card.style.borderLeft = `4px solid ${a.level === 'CRITICAL' || a.level === 'HIGH' ? '#ef4444' : '#f59e0b'}`;
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h4 style="font-size:0.92rem; font-weight:700; color:#fff;">${a.location_name}</h4>
          <span style="font-size:0.72rem; color:var(--text-muted);">${a.alert_id}</span>
        </div>
        <div style="font-size:0.8rem; color:#fca5a5; margin:6px 0;">${a.description}</div>
        <div style="font-size:0.75rem; color:#cbd5e1; background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
          ${a.action_required}
        </div>
      `;
      alertCont.appendChild(card);
    });

    const repRes = await fetch('/api/reports');
    const reports = await repRes.json();
    const repCont = document.getElementById('reports-list-container');
    repCont.innerHTML = '';
    reports.forEach(r => {
      const card = document.createElement('div');
      card.className = 'station-card';
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between;">
          <h4 style="font-size:0.9rem; font-weight:700;">${r.location_name}</h4>
          <span style="font-size:0.72rem; color:var(--accent-cyan); font-weight:600;">${r.observation_type}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--text-muted); margin:2px 0;">Officer: ${r.officer_name} • ${new Date(r.timestamp).toLocaleTimeString()}</div>
        <p style="font-size:0.8rem; color:#cbd5e1; margin-top:6px;">${r.notes}</p>
      `;
      repCont.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading alerts:", err);
  }
}

// 10. Field Report Modal
function openReportModal() {
  document.getElementById('report-modal').classList.add('show');
}

function closeReportModal() {
  document.getElementById('report-modal').classList.remove('show');
}

async function submitFieldReportForm(event) {
  event.preventDefault();
  const payload = {
    lat: parseFloat(document.getElementById('report-lat').value),
    lon: parseFloat(document.getElementById('report-lon').value),
    location_name: document.getElementById('report-location').value,
    district: document.getElementById('report-district').value,
    observation_type: document.getElementById('report-type').value,
    officer_name: document.getElementById('report-officer').value,
    notes: document.getElementById('report-notes').value,
    photo_url: document.getElementById('report-photo').value
  };

  try {
    const res = await fetch('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert("✅ Incident Report Transmitted to State Emergency Center!");
      closeReportModal();
      await loadActiveAlerts();
    }
  } catch (err) {
    alert("Failed to submit report.");
  }
}

// 11. Genuine Manual Risk Calculator (Custom Parameters POST /api/risk/manual)
async function runManualRisk() {
  const lat = parseFloat(document.getElementById('man-lat').value);
  const lon = parseFloat(document.getElementById('man-lon').value);
  const slope = parseFloat(document.getElementById('man-slope').value);
  const elev = parseFloat(document.getElementById('man-elevation').value);
  const suscep = document.getElementById('man-suscep').value;
  const rain6 = parseFloat(document.getElementById('man-rain6').value);
  const rain24 = parseFloat(document.getElementById('man-rain24').value);
  const rain48 = parseFloat(document.getElementById('man-rain48').value);
  const rain7 = parseFloat(document.getElementById('man-rain7').value);
  const soil0_10 = parseFloat(document.getElementById('man-soil0-10').value);
  const soil10_40 = parseFloat(document.getElementById('man-soil10-40').value);

  const badgeEl = document.getElementById('man-result-badge');
  const resultsContainer = document.getElementById('man-results-container');
  const traceBox = document.getElementById('man-trace-box');

  if (isNaN(lat) || isNaN(lon)) {
    badgeEl.textContent = '⚠️ Please specify valid coordinates.';
    badgeEl.style.color = '#f87171';
    return;
  }

  badgeEl.textContent = 'Calculating custom risk model...';
  badgeEl.style.color = '#38bdf8';

  const payload = {
    lat: lat,
    lon: lon,
    slope_deg: isNaN(slope) ? null : slope,
    elevation_m: isNaN(elev) ? null : elev,
    rain_6h: isNaN(rain6) ? null : rain6,
    rain_24h: isNaN(rain24) ? null : rain24,
    rain_48h: isNaN(rain48) ? null : rain48,
    rain_7d: isNaN(rain7) ? null : rain7,
    soil_0_10cm: isNaN(soil0_10) ? null : soil0_10,
    soil_10_40cm: isNaN(soil10_40) ? null : soil10_40,
    susceptibility: suscep
  };

  try {
    const res = await fetch('/api/risk/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const risk = await res.json();

    resultsContainer.style.display = 'block';
    const color = risk.badge_color || '#ef4444';

    document.getElementById('man-card-level').style.borderLeftColor = color;
    const outLevel = document.getElementById('man-out-level');
    outLevel.textContent = `${risk.risk_level} HAZARD`;
    outLevel.style.color = color;

    document.getElementById('man-out-ml').textContent = `${(risk.ml_probability * 100).toFixed(1)}%`;
    document.getElementById('man-out-hazard').textContent = `${risk.risk_score.toFixed(2)}`;
    
    const gsiStatus = (risk.telemetry_metadata && risk.telemetry_metadata.gsi_id_threshold_status) === 'BREACHED'
      ? '⚠️ BREACHED (OVERRIDE)'
      : '✅ NOMINAL';
    const gsiEl = document.getElementById('man-out-gsi');
    gsiEl.textContent = gsiStatus;
    gsiEl.style.color = gsiStatus.includes('BREACHED') ? '#ef4444' : '#10b981';

    document.getElementById('man-out-note').textContent = risk.note || 'Hazard index computed successfully.';

    badgeEl.textContent = `✅ Calculated (${risk.risk_level})`;
    badgeEl.style.color = color;

    traceBox.textContent = JSON.stringify(risk, null, 2);

    // Also update Data Center 5-stage trace with this custom execution
    updateInspectorDisplay(risk);

  } catch (err) {
    badgeEl.textContent = `Calculation failed: ${err.message}`;
    badgeEl.style.color = '#f87171';
  }
}

function applyManualPreset(type) {
  if (type === 'cloudburst') {
    document.getElementById('man-lat').value = "27.6010";
    document.getElementById('man-lon').value = "88.5820";
    document.getElementById('man-slope').value = "44.5";
    document.getElementById('man-elevation').value = "2250";
    document.getElementById('man-suscep').value = "High";
    document.getElementById('man-rain6').value = "55.0";
    document.getElementById('man-rain24').value = "135.0";
    document.getElementById('man-rain48').value = "195.0";
    document.getElementById('man-rain7').value = "340.0";
    document.getElementById('man-soil0-10').value = "0.52";
    document.getElementById('man-soil10-40').value = "0.46";
  } else if (type === 'moderate') {
    document.getElementById('man-lat').value = "27.3389";
    document.getElementById('man-lon').value = "88.6065";
    document.getElementById('man-slope').value = "28.0";
    document.getElementById('man-elevation').value = "1650";
    document.getElementById('man-suscep').value = "Moderate";
    document.getElementById('man-rain6').value = "14.0";
    document.getElementById('man-rain24').value = "38.0";
    document.getElementById('man-rain48').value = "62.0";
    document.getElementById('man-rain7').value = "115.0";
    document.getElementById('man-soil0-10').value = "0.34";
    document.getElementById('man-soil10-40').value = "0.30";
  } else if (type === 'dry_valley') {
    document.getElementById('man-lat').value = "27.1800";
    document.getElementById('man-lon').value = "88.5200";
    document.getElementById('man-slope').value = "12.0";
    document.getElementById('man-elevation').value = "680";
    document.getElementById('man-suscep').value = "Low";
    document.getElementById('man-rain6').value = "0.0";
    document.getElementById('man-rain24').value = "2.0";
    document.getElementById('man-rain48').value = "6.0";
    document.getElementById('man-rain7').value = "18.0";
    document.getElementById('man-soil0-10').value = "0.20";
    document.getElementById('man-soil10-40').value = "0.18";
  }
  runManualRisk();
}

// 12. Data Center Subtab Switching & Real Data Hydration
function switchDcTab(tabName) {
  document.querySelectorAll('.dc-subtab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.dc-pane').forEach(p => {
    p.classList.remove('active');
    p.style.display = 'none';
  });

  const btn = event ? event.currentTarget : null;
  if (btn) btn.classList.add('active');

  const pane = document.getElementById(`dc-pane-${tabName}`);
  if (pane) {
    pane.classList.add('active');
    pane.style.display = 'block';
  }
}

async function refreshDataCenter() {
  try {
    const res = await fetch('/api/data_center/overview');
    if (!res.ok) return;
    const data = await res.json();
    populateDataCenter(data);
  } catch (err) {
    console.error("Failed to load Data Center overview:", err);
  }
}

function populateDataCenter(data) {
  if (!data) return;

  // Weather
  const w = data.weather_data || {};
  const wRainCur = document.getElementById('dc-w-rain-cur');
  if (wRainCur) wRainCur.textContent = `${w.rain_intensity_mmh ?? 0.0} mm/h`;
  const wWindows = document.getElementById('dc-w-rain-windows');
  if (wWindows) wWindows.textContent = `6h: ${w.rain_6h ?? 0}mm • 24h: ${w.rain_24h ?? 0}mm • 48h: ${w.rain_48h ?? 0}mm • 7d: ${w.rain_7d ?? 0}mm`;
  const wTemp = document.getElementById('dc-w-temp');
  if (wTemp) wTemp.textContent = w.current_temperature_c !== undefined ? `${w.current_temperature_c} °C` : '-- °C';
  const wHumid = document.getElementById('dc-w-humid');
  if (wHumid) wHumid.textContent = `Relative Humidity: ${w.current_relative_humidity_pct ?? '--'}% • Wind: ${w.current_wind_speed_kmh ?? '--'} km/h`;
  const wFc = document.getElementById('dc-w-forecast24');
  if (wFc) wFc.textContent = `${w.forecast_24h ?? 0.0} mm`;
  const wStatus = document.getElementById('dc-w-status');
  if (wStatus) {
    wStatus.textContent = w.status || 'LIVE';
    wStatus.style.color = w.status === 'LIVE' ? '#10b981' : (w.status === 'CACHED' ? '#f59e0b' : '#ef4444');
  }
  const wFetch = document.getElementById('dc-w-fetchtime');
  if (wFetch) wFetch.textContent = `Fetched: ${w.last_fetched_iso || 'Live'} (Gangtok Post)`;

  // Hourly forecast sequence table
  const hourlyTbody = document.getElementById('dc-hourly-forecast-tbody');
  if (hourlyTbody && Array.isArray(w.hourly_forecast_24h) && w.hourly_forecast_24h.length > 0) {
    hourlyTbody.innerHTML = '';
    w.hourly_forecast_24h.forEach(row => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
      tr.innerHTML = `
        <td style="padding:6px; font-family:var(--font-mono);">${row.time}</td>
        <td style="padding:6px; font-weight:700; color:${row.precipitation_mm > 5 ? '#ef4444' : (row.precipitation_mm > 1 ? '#fbbf24' : '#38bdf8')}">${row.precipitation_mm} mm</td>
        <td style="padding:6px;">${row.temperature_c !== null ? row.temperature_c + ' °C' : '--'}</td>
        <td style="padding:6px;">${row.relative_humidity_pct !== null ? row.relative_humidity_pct + ' %' : '--'}</td>
      `;
      hourlyTbody.appendChild(tr);
    });
  }

  // Soil moisture
  if (w.soil_layers) {
    const s01 = document.getElementById('dc-soil-0-1');
    if (s01) s01.textContent = `${w.soil_layers['0_1cm'] ?? '--'} m³/m³`;
    const s13 = document.getElementById('dc-soil-1-3');
    if (s13) s13.textContent = `${w.soil_layers['1_3cm'] ?? '--'} m³/m³`;
    const s39 = document.getElementById('dc-soil-3-9');
    if (s39) s39.textContent = `${w.soil_layers['3_9cm'] ?? '--'} m³/m³`;
    const s927 = document.getElementById('dc-soil-9-27');
    if (s927) s927.textContent = `${w.soil_layers['9_27cm'] ?? '--'} m³/m³`;
  }
  const sAgg0 = document.getElementById('dc-soil-agg-0-10');
  if (sAgg0) sAgg0.textContent = `${w.soil_0_10cm ?? '--'} m³/m³`;
  const sAgg10 = document.getElementById('dc-soil-agg-10-40');
  if (sAgg10) sAgg10.textContent = `${w.soil_10_40cm ?? '--'} m³/m³`;

  // Historical Landslides Table
  populateDataCenterHistorical();

  // Susceptibility Table
  populateDataCenterSuscep();
}

async function populateDataCenterHistorical() {
  const tbody = document.getElementById('dc-historical-tbody');
  if (!tbody) return;
  try {
    const res = await fetch('/api/landslides');
    if (!res.ok) return;
    const landslides = await res.json();
    tbody.innerHTML = '';
    (landslides.slice(0, 30) || []).forEach(row => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
      tr.innerHTML = `
        <td style="padding:6px; font-family:var(--font-mono); color:#38bdf8;">${row.id || '--'}</td>
        <td style="padding:6px;">${row.event_date || '--'}</td>
        <td style="padding:6px;">${row.district || '--'}</td>
        <td style="padding:6px;">${row.location_name || '--'}</td>
        <td style="padding:6px; font-family:var(--font-mono); font-size:0.72rem;">${row.lat?.toFixed(3)}, ${row.lon?.toFixed(3)}</td>
        <td style="padding:6px;">${row.type || 'Debris Flow'}</td>
        <td style="padding:6px; font-weight:700; color:#fbbf24;">${row.trigger_rain_24h_mm ?? 0} mm</td>
        <td style="padding:6px;">${row.trigger_rain_7d_mm ?? 0} mm</td>
        <td style="padding:6px;">${row.soil_moisture_0_10cm ?? '--'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Error populating historical table:", e);
  }
}

async function populateDataCenterSuscep() {
  const tbody = document.getElementById('dc-suscep-tbody');
  if (!tbody) return;
  try {
    const res = await fetch('/api/susceptibility');
    if (!res.ok) return;
    const geo = await res.json();
    const features = geo.features || [];
    const countEl = document.getElementById('dc-geo-count');
    if (countEl) countEl.textContent = `${features.length} Polygons (Sikkim NLSM)`;

    tbody.innerHTML = '';
    features.forEach(f => {
      const p = f.properties || {};
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
      const clsColor = p.susceptibility_class === 'High' ? '#ef4444' : (p.susceptibility_class === 'Moderate' ? '#f59e0b' : '#10b981');
      tr.innerHTML = `
        <td style="padding:6px; font-family:var(--font-mono);">${p.zone_id || '--'}</td>
        <td style="padding:6px; font-weight:600;">${p.name || '--'}</td>
        <td style="padding:6px;">${p.district || '--'}</td>
        <td style="padding:6px; font-weight:700; color:${clsColor}">${p.susceptibility_class || '--'}</td>
        <td style="padding:6px;">${p.susceptibility_score ?? '--'}</td>
        <td style="padding:6px;">${p.mean_slope_deg ? p.mean_slope_deg + '°' : '--'}</td>
        <td style="padding:6px; color:var(--text-secondary);">${p.critical_corridor || '--'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Error populating suscep table:", e);
  }
}

function copyTraceJson() {
  const text = document.getElementById('dc-decision-trace').textContent;
  navigator.clipboard.writeText(text).then(() => {
    alert("📋 Raw JSON trace payload copied to clipboard!");
  }).catch(() => {
    alert("Clipboard copy error.");
  });
}

function toggleElement(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'block' : 'none';
}

