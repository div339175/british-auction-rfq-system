import React, { useEffect, useState } from "react";
import { Clock, AlertTriangle, ShieldCheck } from "lucide-react";
import { AuctionStatus } from "../types";

interface CountdownProps {
  closeTimeStr: string;
  forcedCloseTimeStr: string;
  triggerWindowMinutes: number;
  status: AuctionStatus;
}

export const CountdownTimer: React.FC<CountdownProps> = ({
  closeTimeStr,
  forcedCloseTimeStr,
  triggerWindowMinutes,
  status,
}) => {
  const [now, setNow] = useState<Date>(new Date());

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const closeTime = new Date(closeTimeStr);
  const forcedCloseTime = new Date(forcedCloseTimeStr);
  const triggerStartTime = new Date(closeTime.getTime() - triggerWindowMinutes * 60 * 1000);

  const diffMs = closeTime.getTime() - now.getTime();
  const isExpired = diffMs <= 0 || status === "CLOSED" || status === "FORCE_CLOSED";
  const isInTriggerWindow = !isExpired && now >= triggerStartTime && now < closeTime;

  // Format remaining time
  const totalSeconds = Math.max(0, Math.floor(diffMs / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const pad = (n: number) => n.toString().padStart(2, "0");

  const getStatusBadge = () => {
    switch (status) {
      case "ACTIVE":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">ACTIVE</span>;
      case "FORCE_CLOSED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800 border border-red-300">FORCE CLOSED</span>;
      case "CLOSED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700 border border-slate-300">CLOSED</span>;
      case "UPCOMING":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-sky-100 text-sky-800 border border-sky-300">UPCOMING</span>;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-center space-x-3">
        <div className={`p-2.5 rounded-lg ${isExpired ? "bg-slate-100 text-slate-500" : isInTriggerWindow ? "bg-amber-100 text-amber-600 animate-pulse" : "bg-indigo-50 text-indigo-600"}`}>
          <Clock className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Auction Clock</span>
            {getStatusBadge()}
          </div>
          <div className="text-2xl font-mono font-bold tracking-tight text-slate-900 mt-0.5">
            {isExpired ? "00:00:00" : `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {isInTriggerWindow && (
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>In {triggerWindowMinutes}m Anti-Sniping Window (Bids trigger dynamic extension)</span>
          </div>
        )}

        <div className="flex items-center space-x-2 text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
          <ShieldCheck className="w-4 h-4 text-slate-400" />
          <span>
            Hard Cap (Forced Close): <strong className="text-slate-700 font-medium">{forcedCloseTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          </span>
        </div>
      </div>
    </div>
  );
};
