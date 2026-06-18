"use client";

import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, PolarAngleAxis, PolarGrid,
  Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const GREEN = "hsl(152 64% 46%)";
const RED = "hsl(0 78% 60%)";
const AMBER = "hsl(38 92% 55%)";

const tooltipStyle = {
  background: "hsl(220 28% 9%)",
  border: "1px solid hsl(220 20% 18%)",
  borderRadius: 8,
  fontSize: 12,
  color: "hsl(210 20% 92%)",
};

export function PriceArea({ data }: { data: { t: string; price: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id="price" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={GREEN} stopOpacity={0.35} />
            <stop offset="100%" stopColor={GREEN} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="t" tickLine={false} axisLine={false} minTickGap={24} />
        <YAxis tickLine={false} axisLine={false} width={48} domain={["auto", "auto"]} />
        <Tooltip contentStyle={tooltipStyle} />
        <Area type="monotone" dataKey="price" stroke={GREEN} strokeWidth={2} fill="url(#price)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function MetricBars({ data }: { data: { name: string; value: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={false} />
        <YAxis tickLine={false} axisLine={false} width={48} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(220 20% 14%)" }} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.value < 0 ? RED : GREEN} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RiskRadar({ data }: { data: { axis: string; value: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadarChart data={data} outerRadius={90}>
        <PolarGrid stroke="hsl(220 20% 18%)" />
        <PolarAngleAxis dataKey="axis" />
        <Radar dataKey="value" stroke={AMBER} fill={AMBER} fillOpacity={0.3} />
        <Tooltip contentStyle={tooltipStyle} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

export function ScoreBars({ data }: { data: { name: string; value: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart layout="vertical" data={data} margin={{ top: 4, right: 16, bottom: 4, left: 24 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="name" width={120} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(220 20% 14%)" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.value >= 0.8 ? GREEN : d.value >= 0.6 ? AMBER : RED} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
