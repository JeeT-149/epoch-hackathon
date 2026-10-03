import React, { useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { SellingOption } from '../contracts/schemas';

interface MandiMapProps { options: SellingOption[]; }

const MANDI_COORDINATES: Record<string, [number, number]> = {
  mh_nashik_lasalgaon: [20.141, 74.237],
  mh_nashik_pimpalgaon: [20.169, 73.992],
  mh_nashik_local: [20.005, 73.79],
  trader_direct: [20.03, 73.85],
};

export const MandiMap: React.FC<MandiMapProps> = ({ options }) => {
  const [tileError, setTileError] = useState(false);
  const center: [number, number] = [20.08, 74.02];

  if (tileError) {
    return <div className="mt-3 h-32 rounded-xl overflow-hidden relative bg-[#dcebd9] border border-surface-container-high"><div className="absolute inset-0 opacity-60" style={{ backgroundImage: 'linear-gradient(32deg, transparent 48%, #8aaa83 49%, #8aaa83 51%, transparent 52%), linear-gradient(120deg, transparent 48%, #a1bd9b 49%, #a1bd9b 51%, transparent 52%)' }} /><div className="absolute top-5 left-[26%] w-3 h-3 rounded-full bg-primary ring-4 ring-primary/20" /><div className="absolute bottom-7 right-[24%] w-3 h-3 rounded-full bg-tertiary ring-4 ring-tertiary/20" /><div className="absolute bottom-2 left-3 text-[10px] bg-surface-container-lowest px-2 py-1 rounded">Map tiles unavailable · schematic fallback</div></div>;
  }

  return <div className="relative z-0 isolate mt-3 h-56 overflow-hidden rounded-xl border border-surface-container-high"><MapContainer center={center} zoom={9} scrollWheelZoom={false} className="relative z-0 h-full w-full"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{ tileerror: () => setTileError(true) }} />{options.map((option, index) => { const position = MANDI_COORDINATES[option.mandi_id] || [20.08 + index * 0.02, 74.02 + index * 0.02] as [number, number]; const backendRecommended = Boolean((option as any).recommended || (option as any).status === 'RECOMMENDED'); return <CircleMarker key={option.mandi_id} center={position} radius={backendRecommended ? 10 : 7} pathOptions={{ color: backendRecommended ? '#50604d' : '#b56d29', fillColor: backendRecommended ? '#50604d' : '#ebb02d', fillOpacity: 0.95, weight: 2 }}><Popup><strong>{option.mandi_name || option.mandi_id}</strong><br />Net {option.net_return_per_q}/q</Popup></CircleMarker>; })}</MapContainer><span className="absolute bottom-2 left-2 z-10 text-[10px] bg-surface-container-lowest px-2 py-1 rounded">Leaflet · OpenStreetMap</span></div>;
};
