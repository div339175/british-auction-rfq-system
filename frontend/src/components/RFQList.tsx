import React, { useState } from "react";
import { RFQSummary, AuctionStatus } from "../types";
import { ArrowRight, Clock, ShieldAlert, Award, Tag, Filter } from "lucide-react";

interface RFQListProps {
  rfqs: RFQSummary[];
  onSelectRFQ: (id: string) => void;
  isLoading: boolean;
}

export const RFQList: React.FC<RFQListProps> = ({ rfqs, onSelectRFQ, isLoading }) => {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const filteredRfqs = rfqs.filter((r) => {
    if (statusFilter === "ALL") return true;
    return r.status === statusFilter;
  });

  const formatPrice = (val: number | null) => {
    if (val === null || val === undefined) return "No bids yet";
    return `₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  };

  const formatDateTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (status: AuctionStatus) => {
    switch (status) {
      case "ACTIVE":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">ACTIVE</span>;
      case "FORCE_CLOSED":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-red-100 text-red-800 border border-red-300">FORCE CLOSED</span>;
      case "CLOSED":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-700 border border-slate-300">CLOSED</span>;
      case "UPCOMING":
        return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-sky-100 text-sky-800 border border-sky-300">UPCOMING</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">British Auctions</h2>
          <p className="text-xs text-slate-500">Live reverse auctions with automated anti-sniping dynamic extensions</p>
        </div>

        {/* Status Filters */}
        <div className="flex items-center space-x-1 bg-white p-1 rounded-lg border border-slate-200 text-xs shadow-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" />
          {["ALL", "ACTIVE", "UPCOMING", "CLOSED", "FORCE_CLOSED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                statusFilter === st
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-indigo-600 border-t-transparent mb-3"></div>
          <p className="text-sm font-medium">Loading auctions...</p>
        </div>
      ) : filteredRfqs.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
          <p className="text-sm font-medium text-slate-700">No auctions match the selected filter.</p>
          <p className="text-xs text-slate-400 mt-1">Create a new RFQ or switch filter tab to view auctions.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredRfqs.map((rfq) => (
            <div
              key={rfq.id}
              onClick={() => onSelectRFQ(rfq.id)}
              className="group bg-white rounded-xl border border-slate-200 hover:border-indigo-400 p-5 shadow-xs hover:shadow-md transition cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-2 flex-1">
                <div className="flex items-center space-x-2.5">
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                    {rfq.reference_id}
                  </span>
                  {getStatusBadge(rfq.status)}
                  {rfq.extension_count > 0 && (
                    <span className="text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      Extended {rfq.extension_count}x
                    </span>
                  )}
                </div>

                <h3 className="text-base font-semibold text-slate-900 group-hover:text-indigo-600 transition">
                  {rfq.rfq_name}
                </h3>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>Bid Close: <strong className="text-slate-700 font-medium">{formatDateTime(rfq.bid_close_time)}</strong></span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
                    <span>Forced Close: <strong className="text-slate-700 font-medium">{formatDateTime(rfq.forced_bid_close_time)}</strong></span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Tag className="w-3.5 h-3.5 text-slate-400" />
                    <span>Trigger: <strong className="text-slate-700 font-medium">{rfq.extension_trigger_type} ({rfq.trigger_window_minutes}m / +{rfq.extension_duration_minutes}m)</strong></span>
                  </div>
                </div>
              </div>

              {/* Price & Action Block */}
              <div className="flex items-center justify-between md:justify-end gap-6 pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                <div className="text-right">
                  <div className="flex items-center space-x-1 text-xs text-slate-500 justify-end">
                    <Award className="w-3.5 h-3.5 text-amber-500" />
                    <span>Current L1 (Lowest)</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-indigo-600">
                    {formatPrice(rfq.current_lowest_bid)}
                  </div>
                  {rfq.current_lowest_carrier && (
                    <div className="text-[11px] text-slate-500 truncate max-w-[150px]">
                      by {rfq.current_lowest_carrier}
                    </div>
                  )}
                </div>

                <div className="p-2 rounded-lg bg-slate-50 group-hover:bg-indigo-50 text-slate-400 group-hover:text-indigo-600 transition">
                  <ArrowRight className="w-5 h-5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
