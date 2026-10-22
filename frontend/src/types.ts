export type AuctionStatus = "UPCOMING" | "ACTIVE" | "CLOSED" | "FORCE_CLOSED";
export type ExtensionTriggerType = "BID_RECEIVED" | "RANK_CHANGE" | "L1_CHANGE";

export interface RFQSummary {
  id: string;
  reference_id: string;
  rfq_name: string;
  status: AuctionStatus;
  bid_start_time: string;
  bid_close_time: string;
  forced_bid_close_time: string;
  current_lowest_bid: number | null;
  current_lowest_carrier: string | null;
  extension_count: number;
  british_auction_enabled: boolean;
  trigger_window_minutes: number;
  extension_duration_minutes: number;
  extension_trigger_type: ExtensionTriggerType;
}

export interface SupplierRankItem {
  carrier_name: string;
  rank_label: string;
  rank_number: number;
  best_price: number;
  quote_id: string;
  submitted_at: string;
  transit_time_days: number;
  validity_date: string;
}

export interface Quote {
  id: string;
  rfq_id: string;
  carrier_name: string;
  freight_charges: number;
  origin_charges: number;
  destination_charges: number;
  total_price: number;
  transit_time_days: number;
  validity_date: string;
  submitted_at: string;
  rank_at_submission: number | null;
  is_carrier_best: boolean;
}

export interface ActivityLog {
  id: string;
  rfq_id: string;
  event_type: string;
  carrier_name: string | null;
  quote_id: string | null;
  previous_close_time: string | null;
  new_close_time: string | null;
  message: string;
  metadata: Record<string, any> | null;
  created_at: string;
}

export interface RFQDetail {
  id: string;
  reference_id: string;
  rfq_name: string;
  status: AuctionStatus;
  bid_start_time: string;
  bid_close_time: string;
  original_bid_close_time: string;
  forced_bid_close_time: string;
  pickup_service_date: string;
  british_auction_enabled: boolean;
  trigger_window_minutes: number;
  extension_duration_minutes: number;
  extension_trigger_type: ExtensionTriggerType;
  extension_count: number;
  current_lowest_bid: number | null;
  current_lowest_carrier: string | null;
  created_at: string;
  updated_at: string;
  rankings: SupplierRankItem[];
  quotes: Quote[];
  activity_logs: ActivityLog[];
}

export interface CreateRFQPayload {
  reference_id: string;
  rfq_name: string;
  bid_start_time: string;
  bid_close_time: string;
  forced_bid_close_time: string;
  pickup_service_date: string;
  british_auction_enabled: boolean;
  trigger_window_minutes: number;
  extension_duration_minutes: number;
  extension_trigger_type: ExtensionTriggerType;
}

export interface CreateQuotePayload {
  carrier_name: string;
  freight_charges: number;
  origin_charges: number;
  destination_charges: number;
  transit_time_days: number;
  validity_date: string;
}
