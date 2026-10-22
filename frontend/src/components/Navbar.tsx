import React from "react";
import { PlusCircle, Layers, RefreshCw } from "lucide-react";

interface NavbarProps {
  onOpenCreateModal: () => void;
  onRefresh: () => void;
  selectedRfqId: string | null;
  onBackToList: () => void;
  isRefreshing?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenCreateModal,
  onRefresh,
  selectedRfqId,
  onBackToList,
  isRefreshing = false,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={onBackToList}>
          <div className="p-2 bg-indigo-600 rounded-lg text-white shadow-sm">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 leading-tight">British Auction RFQ Engine</h1>
            <p className="text-xs text-slate-500">Autonomous Anti-Sniping & Dynamic Price Discovery</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {selectedRfqId && (
            <button
              onClick={onBackToList}
              className="text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition"
            >
              ← Back to Auctions
            </button>
          )}

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition disabled:opacity-50"
            title="Refresh current data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-indigo-600" : ""}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={onOpenCreateModal}
            className="flex items-center space-x-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-1.5 rounded-lg shadow-sm transition"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New RFQ</span>
          </button>
        </div>
      </div>
    </header>
  );
};
