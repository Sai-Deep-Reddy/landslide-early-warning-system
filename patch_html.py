import os

path = r'backend\app\static\index.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

target = '''          <div id="sim-events-container" style="display:flex; flex-direction:column; gap:8px;">
            <!-- Simulation alarms injected here -->
          </div>
        </div>'''

replacement = target + '''

        <!-- MANUAL RISK CALCULATOR -->
        <div class="simulator-container" style="margin-top:20px;">
          <h2 style="font-size:1.25rem; font-weight:700; margin-bottom:10px;">dY"' Offline Manual Risk Calculator</h2>
          <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:15px;">
            Calculate landslide risk manually if telemetry API fails. Enter observed field data directly into the Risk Engine.
          </p>
          
          <div style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom:15px;">
            <div style="flex:1; min-width:120px;">
              <label style="font-size:0.8rem; display:block; margin-bottom:4px;">Latitude</label>
              <input type="number" id="man-lat" step="0.0001" placeholder="27.33" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid var(--border-color); color:#fff; border-radius:4px;">
            </div>
            <div style="flex:1; min-width:120px;">
              <label style="font-size:0.8rem; display:block; margin-bottom:4px;">Longitude</label>
              <input type="number" id="man-lon" step="0.0001" placeholder="88.62" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid var(--border-color); color:#fff; border-radius:4px;">
            </div>
            <div style="flex:1; min-width:120px;">
              <label style="font-size:0.8rem; display:block; margin-bottom:4px;">Slope (deg)</label>
              <input type="number" id="man-slope" step="0.1" placeholder="35.0" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid var(--border-color); color:#fff; border-radius:4px;">
            </div>
          </div>
          
          <div style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom:20px;">
            <div style="flex:1; min-width:120px;">
              <label style="font-size:0.8rem; display:block; margin-bottom:4px;">Rain 24h (mm)</label>
              <input type="number" id="man-rain24" step="0.1" placeholder="50.0" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid var(--border-color); color:#fff; border-radius:4px;">
            </div>
            <div style="flex:1; min-width:120px;">
              <label style="font-size:0.8rem; display:block; margin-bottom:4px;">Rain 7d (mm)</label>
              <input type="number" id="man-rain7" step="0.1" placeholder="150.0" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid var(--border-color); color:#fff; border-radius:4px;">
            </div>
          </div>
          
          <div style="display:flex; gap:12px; align-items:center;">
            <button class="btn-primary" onclick="runManualRisk()">Calculate Risk</button>
            <span id="man-result" style="font-size:0.9rem; font-weight:bold;"></span>
          </div>
        </div>'''

if target in html:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html.replace(target, replacement))
    print('Replaced successfully.')
else:
    print('Target string not found in index.html')
