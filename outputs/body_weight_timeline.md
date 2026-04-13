# Merged Body Weight Timeline

This view merges old Zepp/Xiaomi scale history with newer Health Connect / VeSync weight entries.

## Trend Chart

This chart compares monthly average bodyweight to monthly best estimated 1RM, e1RM, for squat, bench, and deadlift.
It is normalized so the first available month for each series = 100, which makes trend comparison easier than mixing kg scales.

<svg xmlns="http://www.w3.org/2000/svg" width="980" height="420" viewBox="0 0 980 420">
<style>text{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;fill:#333}.small{font-size:12px}.label{font-size:14px;font-weight:600}.title{font-size:18px;font-weight:700}.grid{stroke:#e5e7eb;stroke-width:1}.axis{stroke:#666;stroke-width:1.5}.bw{stroke:#111827;fill:none;stroke-width:2.5}.sq{stroke:#2563eb;fill:none;stroke-width:2.5}.bp{stroke:#16a34a;fill:none;stroke-width:2.5}.dl{stroke:#dc2626;fill:none;stroke-width:2.5}</style>
<rect x="0" y="0" width="980" height="420" fill="white"/>
<text class="title" x="70" y="20">Bodyweight vs strength trend, monthly, normalized to first available month = 100</text>
<line class="grid" x1="70" y1="365.0" x2="960" y2="365.0" />
<text class="small" x="62" y="369.0" text-anchor="end">97</text>
<line class="grid" x1="70" y1="334.5" x2="960" y2="334.5" />
<text class="small" x="62" y="338.5" text-anchor="end">99</text>
<line class="grid" x1="70" y1="304.1" x2="960" y2="304.1" />
<text class="small" x="62" y="308.1" text-anchor="end">101</text>
<line class="grid" x1="70" y1="273.6" x2="960" y2="273.6" />
<text class="small" x="62" y="277.6" text-anchor="end">103</text>
<line class="grid" x1="70" y1="243.2" x2="960" y2="243.2" />
<text class="small" x="62" y="247.2" text-anchor="end">105</text>
<line class="grid" x1="70" y1="212.7" x2="960" y2="212.7" />
<text class="small" x="62" y="216.7" text-anchor="end">107</text>
<line class="grid" x1="70" y1="182.3" x2="960" y2="182.3" />
<text class="small" x="62" y="186.3" text-anchor="end">109</text>
<line class="grid" x1="70" y1="151.8" x2="960" y2="151.8" />
<text class="small" x="62" y="155.8" text-anchor="end">111</text>
<line class="grid" x1="70" y1="121.4" x2="960" y2="121.4" />
<text class="small" x="62" y="125.4" text-anchor="end">113</text>
<line class="grid" x1="70" y1="90.9" x2="960" y2="90.9" />
<text class="small" x="62" y="94.9" text-anchor="end">115</text>
<line class="grid" x1="70" y1="60.5" x2="960" y2="60.5" />
<text class="small" x="62" y="64.5" text-anchor="end">117</text>
<line class="grid" x1="70" y1="30.0" x2="960" y2="30.0" />
<text class="small" x="62" y="34.0" text-anchor="end">119</text>
<line class="grid" x1="70.0" y1="30" x2="70.0" y2="365" />
<text class="small" x="70.0" y="383" text-anchor="middle">2024-12</text>
<line class="grid" x1="125.6" y1="30" x2="125.6" y2="365" />
<text class="small" x="125.6" y="383" text-anchor="middle">2025-01</text>
<line class="grid" x1="459.4" y1="30" x2="459.4" y2="365" />
<text class="small" x="459.4" y="383" text-anchor="middle">2025-07</text>
<line class="grid" x1="793.1" y1="30" x2="793.1" y2="365" />
<text class="small" x="793.1" y="383" text-anchor="middle">2026-01</text>
<line class="grid" x1="960.0" y1="30" x2="960.0" y2="365" />
<text class="small" x="960.0" y="383" text-anchor="middle">2026-04</text>
<line class="axis" x1="70" y1="365" x2="960" y2="365" />
<line class="axis" x1="70" y1="30" x2="70" y2="365" />
<polyline class="bw" points="70.0,319.3 125.6,281.5 181.2,271.5 236.9,284.8 292.5,268.0 348.1,274.1 403.8,261.2 459.4,265.3 515.0,257.4 570.6,251.4 626.2,264.8 681.9,246.1 737.5,243.7 793.1,232.9 848.8,217.3 904.4,207.7 960.0,205.3" />
<polyline class="sq" points="70.0,319.3 125.6,273.9 181.2,289.2 236.9,269.6 292.5,137.6 348.1,212.4 403.8,161.9 459.4,166.6 515.0,164.2 570.6,164.2 626.2,132.1 681.9,183.8 737.5,158.0 793.1,151.7 848.8,87.5 904.4,62.8 960.0,131.3" />
<polyline class="bp" points="70.0,319.3 125.6,297.1 181.2,307.7 236.9,317.4 292.5,295.1 348.1,295.1 403.8,283.5 459.4,238.1 515.0,159.8 570.6,253.6 626.2,246.8 681.9,241.5 737.5,136.6 793.1,225.5 848.8,183.0 904.4,228.9 960.0,152.1" />
<polyline class="dl" points="125.6,319.3 181.2,312.2 236.9,283.6 292.5,299.2 348.1,296.6 403.8,271.9 459.4,174.8 515.0,179.7 570.6,262.8 626.2,304.4 681.9,287.5 737.5,217.0 793.1,238.1 848.8,246.6 904.4,186.2 960.0,251.5" />
<line x1="70" y1="36" x2="92" y2="36" stroke="#111827" stroke-width="3" />
<text class="small" x="98" y="40">Bodyweight</text>
<line x1="280" y1="36" x2="302" y2="36" stroke="#2563eb" stroke-width="3" />
<text class="small" x="308" y="40">Squat e1RM</text>
<line x1="490" y1="36" x2="512" y2="36" stroke="#16a34a" stroke-width="3" />
<text class="small" x="518" y="40">Bench e1RM</text>
<line x1="700" y1="36" x2="722" y2="36" stroke="#dc2626" stroke-width="3" />
<text class="small" x="728" y="40">Deadlift e1RM</text>
<text class="label" x="490.0" y="408" text-anchor="middle">Month</text>
<text class="label" x="22" y="210.0" text-anchor="middle" transform="rotate(-90 22 210.0)">Index, first available month = 100</text>
</svg>

## Overall Summary

- Logged days: 684
- Average bodyweight: 75.7 kg
- Lowest bodyweight: 69.5 kg on 2024-01-04
- Highest bodyweight: 81.4 kg on 2019-03-15
- First logged day: 2019-03-15 (81.4 kg, Zepp Life)
- Last logged day: 2026-04-12 (79.7 kg, VeSync)
- Net change: -1.7 kg

## Month-by-Month Summary

| Month | Days | Avg | Low | High | Start | End | Delta | Main source | Best squat e1RM | Best bench e1RM | Best deadlift e1RM |
|---|---:|---:|---|---|---:|---:|---:|---|---:|---:|---:|
| 2019-03 | 13 | 79.4 kg | 78.7 kg (2019-03-30) | 81.4 kg (2019-03-15) | 81.4 kg | 78.7 kg | -2.7 kg | Zepp Life | - kg | - kg | - kg |
| 2019-04 | 13 | 79.2 kg | 78.5 kg (2019-04-12) | 80.2 kg (2019-04-28) | 79.6 kg | 78.5 kg | -1.1 kg | Zepp Life | - kg | - kg | - kg |
| 2019-05 | 7 | 77.8 kg | 77.4 kg (2019-05-06) | 78.5 kg (2019-05-01) | 78.5 kg | 77.9 kg | -0.6 kg | Zepp Life | - kg | - kg | - kg |
| 2019-06 | 28 | 77.1 kg | 75 kg (2019-06-30) | 79.4 kg (2019-06-11) | 78.4 kg | 75 kg | -3.4 kg | Zepp Life | - kg | - kg | - kg |
| 2019-07 | 3 | 75.2 kg | 75 kg (2019-07-01) | 75.5 kg (2019-07-05) | 75 kg | 75.5 kg | +0.5 kg | Zepp Life | - kg | - kg | - kg |
| 2019-08 | 29 | 72.1 kg | 70.3 kg (2019-08-28) | 74.5 kg (2019-08-04) | 73.9 kg | 72.6 kg | -1.3 kg | Zepp Life | - kg | - kg | - kg |
| 2019-09 | 28 | 73 kg | 72 kg (2019-09-28) | 74.9 kg (2019-09-23) | 73.6 kg | 72 kg | -1.6 kg | Zepp Life | - kg | - kg | - kg |
| 2023-11 | 2 | 74.9 kg | 74.9 kg (2023-11-28) | 74.9 kg (2023-11-28) | 74.9 kg | 74.9 kg | 0 kg | Zepp Life | - kg | - kg | - kg |
| 2023-12 | 27 | 74.9 kg | 74.2 kg (2023-12-19) | 75.8 kg (2023-12-05) | 75.8 kg | 75 kg | -0.8 kg | Zepp Life | - kg | - kg | - kg |
| 2024-01 | 30 | 74.3 kg | 69.5 kg (2024-01-04) | 76.1 kg (2024-01-21) | 75.6 kg | 69.6 kg | -6 kg | Zepp Life | - kg | - kg | - kg |
| 2024-02 | 19 | 74.7 kg | 73.9 kg (2024-02-29) | 76.2 kg (2024-02-04) | 74.2 kg | 73.9 kg | -0.3 kg | Zepp Life | - kg | - kg | - kg |
| 2024-03 | 15 | 73.4 kg | 71.7 kg (2024-03-26) | 75.3 kg (2024-03-03) | 75 kg | 72.7 kg | -2.3 kg | Zepp Life | - kg | - kg | - kg |
| 2024-04 | 30 | 72.5 kg | 70.1 kg (2024-04-07) | 73.5 kg (2024-04-29) | 73 kg | 72.3 kg | -0.7 kg | Zepp Life | - kg | - kg | - kg |
| 2024-05 | 11 | 73.5 kg | 70.2 kg (2024-05-29) | 75.5 kg (2024-05-19) | 72.8 kg | 73.3 kg | +0.5 kg | Zepp Life | - kg | - kg | - kg |
| 2024-06 | 29 | 73.9 kg | 70.4 kg (2024-06-01) | 75.4 kg (2024-06-16) | 70.4 kg | 74.5 kg | +4.1 kg | Zepp Life | - kg | - kg | - kg |
| 2024-07 | 14 | 74.1 kg | 71.3 kg (2024-07-15) | 74.8 kg (2024-07-18) | 74.5 kg | 74.8 kg | +0.3 kg | Zepp Life | - kg | - kg | - kg |
| 2024-09 | 23 | 74.2 kg | 70.9 kg (2024-09-12) | 75.5 kg (2024-09-24) | 73.5 kg | 71.2 kg | -2.3 kg | Zepp Life | - kg | - kg | - kg |
| 2024-10 | 23 | 74.2 kg | 71 kg (2024-10-04) | 75.6 kg (2024-10-06) | 74.8 kg | 74.1 kg | -0.7 kg | Zepp Life | - kg | - kg | - kg |
| 2024-11 | 24 | 74.6 kg | 71.1 kg (2024-11-30) | 76.1 kg (2024-11-09) | 74.9 kg | 71.1 kg | -3.8 kg | Zepp Life | - kg | - kg | - kg |
| 2024-12 | 17 | 74 kg | 71 kg (2024-12-12) | 75.9 kg (2024-12-15) | 75.3 kg | 71.2 kg | -4.1 kg | Zepp Life | 162 kg | 131.2 kg | - kg |
| 2025-01 | 11 | 75.9 kg | 74.9 kg (2025-01-29) | 77.1 kg (2025-01-20) | 75.6 kg | 74.9 kg | -0.7 kg | Zepp Life | 166.8 kg | 133.2 kg | 195.4 kg |
| 2025-02 | 4 | 76.3 kg | 76.1 kg (2025-02-06) | 76.7 kg (2025-02-08) | 76.1 kg | 76.3 kg | +0.2 kg | Zepp Life | 165.2 kg | 132.2 kg | 196.3 kg |
| 2025-03 | 12 | 75.7 kg | 74.6 kg (2025-03-21) | 76.5 kg (2025-03-10) | 75.9 kg | 76.2 kg | +0.3 kg | Zepp Life | 167.3 kg | 131.4 kg | 200 kg |
| 2025-04 | 25 | 76.5 kg | 71.3 kg (2025-04-15) | 77.9 kg (2025-04-21) | 76.1 kg | 76.8 kg | +0.7 kg | Zepp Life | 181.3 kg | 133.3 kg | 198 kg |
| 2025-05 | 19 | 76.2 kg | 71.6 kg (2025-05-16) | 77.6 kg (2025-05-17) | 71.8 kg | 76.7 kg | +4.9 kg | Zepp Life | 173.4 kg | 133.3 kg | 198.3 kg |
| 2025-06 | 30 | 76.8 kg | 72 kg (2025-06-22) | 77.6 kg (2025-06-14) | 76.7 kg | 76.9 kg | +0.2 kg | Zepp Life | 178.8 kg | 134.3 kg | 201.5 kg |
| 2025-07 | 23 | 76.6 kg | 75.8 kg (2025-07-04) | 77.1 kg (2025-07-05) | 76.9 kg | 76.3 kg | -0.6 kg | Zepp Life | 178.3 kg | 138.2 kg | 214 kg |
| 2025-08 | 12 | 77 kg | 76.4 kg (2025-08-20) | 77.6 kg (2025-08-29) | 76.8 kg | 77.6 kg | +0.8 kg | Zepp Life | 178.5 kg | 145 kg | 213.3 kg |
| 2025-09 | 30 | 77.3 kg | 76.3 kg (2025-09-23) | 78.1 kg (2025-09-13) | 77.6 kg | 76.9 kg | -0.7 kg | Zepp Life | 178.5 kg | 136.9 kg | 202.7 kg |
| 2025-10 | 18 | 76.7 kg | 72.4 kg (2025-10-05) | 77.7 kg (2025-10-04) | 76.9 kg | 76.9 kg | 0 kg | Zepp Life | 181.9 kg | 137.5 kg | 197.3 kg |
| 2025-11 | 28 | 77.6 kg | 74.4 kg (2025-11-17) | 78.7 kg (2025-11-30) | 78.3 kg | 78.7 kg | +0.4 kg | Zepp Life | 176.4 kg | 138 kg | 199.5 kg |
| 2025-12 | 21 | 77.7 kg | 77 kg (2025-12-10) | 78.4 kg (2025-12-12) | 77.6 kg | 77.9 kg | +0.3 kg | VeSync | 179.2 kg | 147 kg | 208.5 kg |
| 2026-01 | 23 | 78.2 kg | 77.3 kg (2026-01-28) | 79 kg (2026-01-25) | 78.6 kg | 78.8 kg | +0.2 kg | VeSync | 179.8 kg | 139.3 kg | 205.8 kg |
| 2026-02 | 11 | 79 kg | 78.2 kg (2026-02-01) | 79.6 kg (2026-02-27) | 78.2 kg | 79.6 kg | +1.4 kg | VeSync | 186.7 kg | 143 kg | 204.8 kg |
| 2026-03 | 23 | 79.4 kg | 78.4 kg (2026-03-03) | 80.5 kg (2026-03-29) | 80.3 kg | 79.6 kg | -0.7 kg | VeSync | 189.3 kg | 139 kg | 212.5 kg |
| 2026-04 | 9 | 79.6 kg | 79.1 kg (2026-04-08) | 80.3 kg (2026-04-05) | 79.2 kg | 79.7 kg | +0.5 kg | VeSync | 182 kg | 145.7 kg | 204.1 kg |

## Recent Daily Entries

| Date | Weight | Source |
|---|---:|---|
| 2026-03-03 | 78.4 kg | VeSync |
| 2026-03-04 | 78.4 kg | VeSync |
| 2026-03-06 | 79.4 kg | VeSync |
| 2026-03-08 | 79.5 kg | VeSync |
| 2026-03-09 | 78.9 kg | VeSync |
| 2026-03-10 | 79.3 kg | VeSync |
| 2026-03-11 | 79.1 kg | VeSync |
| 2026-03-13 | 79.6 kg | VeSync |
| 2026-03-15 | 80.1 kg | VeSync |
| 2026-03-16 | 79.3 kg | VeSync |
| 2026-03-17 | 78.8 kg | VeSync |
| 2026-03-18 | 79.2 kg | VeSync |
| 2026-03-20 | 79.8 kg | VeSync |
| 2026-03-22 | 80 kg | VeSync |
| 2026-03-23 | 78.8 kg | VeSync |
| 2026-03-24 | 79.8 kg | VeSync |
| 2026-03-25 | 79.6 kg | VeSync |
| 2026-03-27 | 80.2 kg | VeSync |
| 2026-03-29 | 80.5 kg | VeSync |
| 2026-03-30 | 79.6 kg | VeSync |
| 2026-03-31 | 79.6 kg | VeSync |
| 2026-04-01 | 79.2 kg | VeSync |
| 2026-04-02 | 79.3 kg | VeSync |
| 2026-04-03 | 79.8 kg | VeSync |
| 2026-04-05 | 80.3 kg | VeSync |
| 2026-04-06 | 79.4 kg | VeSync |
| 2026-04-07 | 79.2 kg | VeSync |
| 2026-04-08 | 79.1 kg | VeSync |
| 2026-04-10 | 80.1 kg | VeSync |
| 2026-04-12 | 79.7 kg | VeSync |
