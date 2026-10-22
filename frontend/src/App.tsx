import { useState, useEffect, useCallback } from "react";
import { RFQSummary, RFQDetail as RFQDetailType } from "./types";
import { fetchRFQs, fetchRFQDetails } from "./api";
import { Navbar } from "./components/Navbar";
import { RFQList } from "./components/RFQList";
import { RFQDetail } from "./components/RFQDetail";
import { CreateRFQModal } from "./components/CreateRFQModal";

export function App() {
  const [rfqs, setRfqs] = useState<RFQSummary[]>([]);
  const [selectedRfqId, setSelectedRfqId] = useState<string | null>(null);
  const [currentRfqDetail, setCurrentRfqDetail] = useState<RFQDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Load RFQ list
  const loadRFQs = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchRFQs();
      setRfqs(data);
    } catch (err) {
      console.error("Error loading RFQs:", err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Load specific RFQ details
  const loadRFQDetails = useCallback(async (id: string) => {
    setIsRefreshing(true);
    try {
      const data = await fetchRFQDetails(id);
      setCurrentRfqDetail(data);
    } catch (err) {
      console.error("Error loading RFQ details:", err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadRFQs();
  }, [loadRFQs]);

  useEffect(() => {
    if (selectedRfqId) {
      loadRFQDetails(selectedRfqId);
    } else {
      setCurrentRfqDetail(null);
    }
  }, [selectedRfqId, loadRFQDetails]);

  const handleRefresh = () => {
    if (selectedRfqId) {
      loadRFQDetails(selectedRfqId);
    } else {
      loadRFQs();
    }
  };

  const handleSelectRFQ = (id: string) => {
    setSelectedRfqId(id);
  };

  const handleBackToList = () => {
    setSelectedRfqId(null);
    loadRFQs();
  };

  const handleRFQCreated = (newRfq: RFQDetailType) => {
    setSelectedRfqId(newRfq.id);
    setCurrentRfqDetail(newRfq);
    loadRFQs();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        onOpenCreateModal={() => setIsCreateModalOpen(true)}
        onRefresh={handleRefresh}
        selectedRfqId={selectedRfqId}
        onBackToList={handleBackToList}
        isRefreshing={isRefreshing}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {selectedRfqId && currentRfqDetail ? (
          <RFQDetail rfq={currentRfqDetail} onRefresh={() => loadRFQDetails(selectedRfqId)} />
        ) : (
          <RFQList rfqs={rfqs} onSelectRFQ={handleSelectRFQ} isLoading={isLoading} />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 mt-12 text-center text-xs text-slate-400">
        <p>British Auction RFQ System • reverse auction mechanics with anti-sniping dynamic extensions & hard forced close ceiling.</p>
      </footer>

      <CreateRFQModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={handleRFQCreated}
      />
    </div>
  );
}

export default App;
