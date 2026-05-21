import type { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  icon: LucideIcon;
  value: number | string;
  label: string;
  color: string;
  bgColor: string;
}

export default function StatsCard({
  icon: Icon,
  value,
  label,
  color,
  bgColor,
}: StatsCardProps) {
  return (
    <div
      className="bg-white rounded-lg p-5 border border-[#e5edf5] transition-shadow duration-150 hover:shadow-md"
      style={{
        boxShadow:
          'rgba(50,50,93,0.08) 0px 2px 8px -2px, rgba(0,0,0,0.05) 0px 4px 12px -4px',
      }}
    >
      <div className="flex items-center gap-4">
        <div
          className="w-11 h-11 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: bgColor }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        <div>
          <p className="text-2xl font-semibold text-[#061b31] tracking-tight">
            {value}
          </p>
          <p className="text-sm text-[#64748d] mt-0.5">{label}</p>
        </div>
      </div>
    </div>
  );
}
