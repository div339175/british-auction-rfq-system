import React, { useState, useEffect } from "react";
import { RFQDetail as RFQDetailType, CreateQuotePayload } from "../types";
import { CountdownTimer } from "./CountdownTimer";
import { submitQuote } from "../api";
import {
  Award,
  Send,
  History,
  Info,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Truck,
  TrendingUp,
  Tag,
} from "lucide-react";

interface RFQDetailProps {
  rfq: RFQDetailType;
  onRefresh: () => void;
}

export const RFQDetail: React.FC<RFQDetailProps> = ({ rfq, onRefresh }) => {
  // Quote submission form state
  const [carrierName, setCarrierName] = useState("");
  const [freightCharges, setFreightCharges] = useState<string>("");
  const [originCharges, setOriginCharges] = useState<string>("");
  const [destinationCharges, setDestinationCharges] = useState<string>("");
  const [transitDays, setTransitDays] = useState<string>("3");
  const [validityDate, setValidityDate] = useState<string>("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [quoteSortOrder, setQuoteSortOrder] = useState<"lowest_price" | "newest">("lowest_price");

  // Auto-polling interval: 3 seconds for active auctions
  useEffect(() => {
    if (rfq.status !== "ACTIVE") return;
    const interval = setInterval(() => {
      onRefresh();
    }, 3000);
    return () => clearInterval(interval);
  }, [rfq.status, onRefresh]);

  // Set default validity date to 14 days in future
  useEffect(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    setValidityDate(d.toISOString().slice(0, 16));
  }, []);

  const totalCalculated =
    (parseFloat(freightCharges) || 0) +
    (parseFloat(originCharges) || 0) +
    (parseFloat(destinationCharges) || 0);

  const handleSubmitQuote = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionNotice(null);

    if (!carrierName.trim()) {
      setActionNotice({ type: "error", text: "Please provide a valid Carrier Name." });
      return;
    }

    if (totalCalculated <= 0) {
      setActionNotice({ type: "error", text: "Total price (freight + origin + destination) must exceed ₹0." });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: CreateQuotePayload = {
        carrier_name: carrierName.trim(),
        freight_charges: parseFloat(freightCharges) || 0,
        origin_charges: parseFloat(originCharges) || 0,
        destination_charges: parseFloat(destinationCharges) || 0,
        transit_time_days: parseInt(transitDays) || 1,
        validity_date: new Date(validityDate).toISOString(),
      };

      const res = await submitQuote(rfq.id, payload);
      setActionNotice({
        type: "success",
        text: res.message || "Quote successfully submitted!",
      });

      // Clear price fields to prevent accidental duplicate submission
      setFreightCharges("");
      setOriginCharges("");
      setDestinationCharges("");
      onRefresh();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        text: err.message || "Failed to submit quote.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatPrice = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "—";
    return `₹${Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  };

  const formatDateTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Countdown Timer */}
      <div className="space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                {rfq.reference_id}
              </span>
              <span className="text-xs text-slate-500">
                Created: {new Date(rfq.created_at).toLocaleDateString()}
              </span>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mt-1">{rfq.rfq_name}</h2>
          </div>

          <div className="flex items-center space-x-3 text-xs text-slate-500">
            <div className="flex items-center space-x-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Service Date: <strong>{new Date(rfq.pickup_service_date).toLocaleDateString()}</strong></span>
            </div>
          </div>
        </div>

        <CountdownTimer
          closeTimeStr={rfq.bid_close_time}
          forcedCloseTimeStr={rfq.forced_bid_close_time}
          triggerWindowMinutes={rfq.trigger_window_minutes}
          status={rfq.status}
        />
      </div>

      {/* Auction Configuration Summary Card */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 flex items-center space-x-1">
            <Award className="w-3.5 h-3.5 text-amber-500" />
            <span>Current Lowest (L1)</span>
          </div>
          <div className="text-xl font-bold font-mono text-indigo-600 mt-1">
            {formatPrice(rfq.current_lowest_bid)}
          </div>
          <div className="text-xs text-slate-500 truncate mt-0.5">
            {rfq.current_lowest_carrier ? `Carrier: ${rfq.current_lowest_carrier}` : "No bids yet"}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 flex items-center space-x-1">
            <TrendingUp className="w-3.5 h-3.5 text-indigo-500" />
            <span>Total Extensions</span>
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
            {rfq.extension_count}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            +{rfq.extension_duration_minutes} min per trigger
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 flex items-center space-x-1">
            <Tag className="w-3.5 h-3.5 text-slate-400" />
            <span>Trigger Window (X)</span>
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
            {rfq.trigger_window_minutes} min
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Rule: {rfq.extension_trigger_type}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 flex items-center space-x-1">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span>Initial Scheduled Close</span>
          </div>
          <div className="text-sm font-semibold font-mono text-slate-900 mt-1">
            {new Date(rfq.original_bid_close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Forced: {new Date(rfq.forced_bid_close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Supplier Rankings & Quote History */}
        <div className="lg:col-span-2 space-y-6">
          {/* Supplier Ranking Leaderboard */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Award className="w-4 h-4 text-amber-500" />
                <h3 className="text-sm font-bold text-slate-900">Supplier Ranking Leaderboard (Sorted by Price)</h3>
              </div>
              <span className="text-xs text-slate-500">{rfq.rankings.length} Active Competitors</span>
            </div>

            {rfq.rankings.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                No quotes submitted yet. Use the form below to place the opening bid!
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase tracking-wider">
                    <tr>
                      <th className="py-2.5 px-4">Rank</th>
                      <th className="py-2.5 px-4">Supplier / Carrier</th>
                      <th className="py-2.5 px-4">Best Total Quote</th>
                      <th className="py-2.5 px-4">Committed Transit</th>
                      <th className="py-2.5 px-4">Validity</th>
                      <th className="py-2.5 px-4">Submitted At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {rfq.rankings.map((item) => (
                      <tr
                        key={item.quote_id}
                        className={`hover:bg-slate-50 transition ${
                          item.rank_label === "L1" ? "bg-amber-50/40 font-semibold" : ""
                        }`}
                      >
                        <td className="py-3 px-4">
                          <span
                            className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold ${
                              item.rank_label === "L1"
                                ? "bg-amber-100 text-amber-800 border border-amber-300"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {item.rank_label}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-900 flex items-center space-x-2">
                          <Truck className="w-3.5 h-3.5 text-slate-400" />
                          <span>{item.carrier_name}</span>
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-indigo-600">
                          {formatPrice(item.best_price)}
                        </td>
                        <td className="py-3 px-4 text-slate-600">{item.transit_time_days} days</td>
                        <td className="py-3 px-4 text-slate-500">{new Date(item.validity_date).toLocaleDateString()}</td>
                        <td className="py-3 px-4 text-slate-500">{formatDateTime(item.submitted_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Interactive Quote Submission Form */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center space-x-2 mb-4 border-b border-slate-100 pb-3">
              <Send className="w-4 h-4 text-indigo-600" />
              <h3 className="text-sm font-bold text-slate-900">Submit Quote / Place Competitive Bid</h3>
            </div>

            {actionNotice && (
              <div
                className={`mb-4 p-3 rounded-lg text-xs flex items-start space-x-2 ${
                  actionNotice.type === "success"
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    : "bg-red-50 text-red-800 border border-red-200"
                }`}
              >
                {actionNotice.type === "success" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                )}
                <span>{actionNotice.text}</span>
              </div>
            )}

            <form onSubmit={handleSubmitQuote} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Carrier / Supplier Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Maersk Logistics"
                    value={carrierName}
                    onChange={(e) => setCarrierName(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Committed Transit Time (Days) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={transitDays}
                    onChange={(e) => setTransitDays(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Price Breakdown Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Freight Charges (₹) *
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    placeholder="45000"
                    value={freightCharges}
                    onChange={(e) => setFreightCharges(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Origin Charges (₹) *
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    placeholder="5000"
                    value={originCharges}
                    onChange={(e) => setOriginCharges(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Destination Charges (₹) *
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    placeholder="5000"
                    value={destinationCharges}
                    onChange={(e) => setDestinationCharges(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Computed Total & Quote Validity */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span className="text-xs text-slate-500">Calculated Total Bid Price:</span>
                  <div className="text-xl font-bold font-mono text-indigo-600">
                    {formatPrice(totalCalculated)}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Validity of Quote *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={validityDate}
                    onChange={(e) => setValidityDate(e.target.value)}
                    className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || rfq.status === "CLOSED" || rfq.status === "FORCE_CLOSED"}
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-semibold rounded-lg shadow-sm transition flex items-center justify-center space-x-2"
              >
                <Send className="w-4 h-4" />
                <span>
                  {isSubmitting
                    ? "Transacting Bid..."
                    : rfq.status === "CLOSED" || rfq.status === "FORCE_CLOSED"
                    ? "Auction is Closed"
                    : "Submit Competitive Quote"}
                </span>
              </button>
            </form>
          </div>

          {/* Complete Quote History Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
            <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-slate-900">Submitted Quotes History ({rfq.quotes.length})</h3>
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-slate-500 font-medium">Sort by:</span>
                <select
                  value={quoteSortOrder}
                  onChange={(e) => setQuoteSortOrder(e.target.value as "lowest_price" | "newest")}
                  className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-700 font-medium text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="lowest_price">Lowest Price First</option>
                  <option value="newest">Newest First</option>
                </select>
              </div>
            </div>
            {rfq.quotes.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-xs">No quotes recorded yet.</div>
            ) : (
              <div className="overflow-x-auto max-h-72 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase tracking-wider sticky top-0">
                    <tr>
                      <th className="py-2 px-3">Carrier</th>
                      <th className="py-2 px-3">Freight</th>
                      <th className="py-2 px-3">Origin</th>
                      <th className="py-2 px-3">Dest</th>
                      <th className="py-2 px-3">Total</th>
                      <th className="py-2 px-3">Rank at Bid</th>
                      <th className="py-2 px-3">Submitted At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {[...rfq.quotes]
                      .sort((a, b) => {
                        if (quoteSortOrder === "lowest_price") {
                          return Number(a.total_price) - Number(b.total_price);
                        }
                        return new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime();
                      })
                      .map((q) => (
                        <tr key={q.id} className="hover:bg-slate-50">
                          <td className="py-2 px-3 font-medium text-slate-900">{q.carrier_name}</td>
                          <td className="py-2 px-3 font-mono text-slate-600">{formatPrice(q.freight_charges)}</td>
                          <td className="py-2 px-3 font-mono text-slate-600">{formatPrice(q.origin_charges)}</td>
                          <td className="py-2 px-3 font-mono text-slate-600">{formatPrice(q.destination_charges)}</td>
                          <td className="py-2 px-3 font-mono font-semibold text-indigo-600">{formatPrice(q.total_price)}</td>
                          <td className="py-2 px-3">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[11px]">
                              L{q.rank_at_submission || "—"}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-400">{formatDateTime(q.submitted_at)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Real-time Chronological Activity Log */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <History className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">Activity Log & Audit Trail</h3>
              </div>
              <span className="text-[11px] text-slate-400">Live feed</span>
            </div>

            <div className="p-4 max-h-[680px] overflow-y-auto space-y-3">
              {rfq.activity_logs.length === 0 ? (
                <div className="text-center text-slate-400 text-xs py-8">No activity logs recorded.</div>
              ) : (
                rfq.activity_logs.map((log) => {
                  const isExtension =
                    log.event_type === "AUCTION_EXTENDED" || log.event_type === "EXTENSION_CAPPED";
                  return (
                    <div
                      key={log.id}
                      className={`p-3 rounded-lg border text-xs space-y-1.5 transition ${
                        isExtension
                          ? "bg-amber-50/70 border-amber-200"
                          : log.event_type === "AUCTION_CLOSED" || log.event_type === "AUCTION_FORCE_CLOSED"
                          ? "bg-red-50/70 border-red-200"
                          : "bg-slate-50 border-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`font-semibold text-[11px] px-2 py-0.5 rounded ${
                            isExtension
                              ? "bg-amber-100 text-amber-900 border border-amber-300"
                              : log.event_type === "AUCTION_CLOSED" || log.event_type === "AUCTION_FORCE_CLOSED"
                              ? "bg-red-100 text-red-800"
                              : "bg-indigo-50 text-indigo-700"
                          }`}
                        >
                          {log.event_type}
                        </span>
                        <span className="text-[10px] text-slate-400">{formatDateTime(log.created_at)}</span>
                      </div>

                      <p className="text-slate-800 font-medium text-xs leading-relaxed">{log.message}</p>

                      {isExtension && log.previous_close_time && log.new_close_time && (
                        <div className="text-[11px] text-amber-900 font-mono bg-white/80 p-1.5 rounded border border-amber-200/60">
                          {formatDateTime(log.previous_close_time)} → <strong>{formatDateTime(log.new_close_time)}</strong>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
