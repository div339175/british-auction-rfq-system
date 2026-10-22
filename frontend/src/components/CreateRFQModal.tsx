import React, { useState } from "react";
import { CreateRFQPayload, ExtensionTriggerType, RFQDetail } from "../types";
import { createRFQ } from "../api";
import { X, AlertCircle } from "lucide-react";

interface CreateRFQModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (rfq: RFQDetail) => void;
}

export const CreateRFQModal: React.FC<CreateRFQModalProps> = ({ isOpen, onClose, onCreated }) => {
  const now = new Date();
  const formatForInput = (d: Date) => d.toISOString().slice(0, 16);

  const [rfqName, setRfqName] = useState("");
  const [referenceId, setReferenceId] = useState(`RFQ-${Date.now().toString().slice(-6)}`);
  const [bidStartTime, setBidStartTime] = useState(formatForInput(now));
  
  // Default close time: 30 minutes from now
  const defaultClose = new Date(now.getTime() + 30 * 60 * 1000);
  const [bidCloseTime, setBidCloseTime] = useState(formatForInput(defaultClose));

  // Default forced close: 45 minutes from now
  const defaultForced = new Date(now.getTime() + 45 * 60 * 1000);
  const [forcedBidCloseTime, setForcedBidCloseTime] = useState(formatForInput(defaultForced));

  // Default pickup date: 5 days from now
  const defaultPickup = new Date(now.getTime() + 5 * 24 * 60 * 60 * 1000);
  const [pickupDate, setPickupDate] = useState(formatForInput(defaultPickup));

  const [triggerWindow, setTriggerWindow] = useState("10");
  const [extensionDuration, setExtensionDuration] = useState("5");
  const [triggerType, setTriggerType] = useState<ExtensionTriggerType>("BID_RECEIVED");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const start = new Date(bidStartTime);
    const close = new Date(bidCloseTime);
    const forced = new Date(forcedBidCloseTime);

    if (close <= start) {
      setErrorMsg("Bid Close Time must be strictly later than Bid Start Time.");
      return;
    }
    if (forced <= close) {
      setErrorMsg("Forced Bid Close Time must be strictly later than Bid Close Time.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: CreateRFQPayload = {
        reference_id: referenceId.trim(),
        rfq_name: rfqName.trim(),
        bid_start_time: start.toISOString(),
        bid_close_time: close.toISOString(),
        forced_bid_close_time: forced.toISOString(),
        pickup_service_date: new Date(pickupDate).toISOString(),
        british_auction_enabled: true,
        trigger_window_minutes: parseInt(triggerWindow) || 10,
        extension_duration_minutes: parseInt(extensionDuration) || 5,
        extension_trigger_type: triggerType,
      };

      const created = await createRFQ(payload);
      onCreated(created);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create RFQ.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">Create New British Auction RFQ</h3>
            <p className="text-xs text-slate-500">Configure parameters, anti-sniping window, and forced close deadline</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-800 text-xs flex items-start space-x-2 border border-red-200">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">RFQ Reference ID *</label>
              <input
                type="text"
                required
                value={referenceId}
                onChange={(e) => setReferenceId(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 font-mono focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Pickup / Service Date *</label>
              <input
                type="datetime-local"
                required
                value={pickupDate}
                onChange={(e) => setPickupDate(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">RFQ Name / Shipment Title *</label>
            <input
              type="text"
              required
              placeholder="e.g. 40ft HC Container - JNPT to Hamburg Port"
              value={rfqName}
              onChange={(e) => setRfqName(e.target.value)}
              className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Bid Start Time *</label>
              <input
                type="datetime-local"
                required
                value={bidStartTime}
                onChange={(e) => setBidStartTime(e.target.value)}
                className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Bid Close Time *</label>
              <input
                type="datetime-local"
                required
                value={bidCloseTime}
                onChange={(e) => setBidCloseTime(e.target.value)}
                className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Forced Close Time *</label>
              <input
                type="datetime-local"
                required
                value={forcedBidCloseTime}
                onChange={(e) => setForcedBidCloseTime(e.target.value)}
                className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>
          </div>

          {/* British Auction Anti-Sniping Configuration */}
          <div className="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 space-y-3">
            <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">
              British Auction Anti-Sniping Settings
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Trigger Window X (Minutes) *
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={triggerWindow}
                  onChange={(e) => setTriggerWindow(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Extension Duration Y (Minutes) *
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={extensionDuration}
                  onChange={(e) => setExtensionDuration(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Extension Trigger Condition *
              </label>
              <select
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value as ExtensionTriggerType)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                <option value="BID_RECEIVED">Bid Received in Last X Minutes (Any valid quote extends)</option>
                <option value="RANK_CHANGE">Any Supplier Rank Change in Last X Minutes</option>
                <option value="L1_CHANGE">Lowest Bidder (L1) Rank Change in Last X Minutes</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg shadow-sm transition"
            >
              {isSubmitting ? "Creating..." : "Create RFQ Auction"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
