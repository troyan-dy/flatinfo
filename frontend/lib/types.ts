export type Recommendation = "buy" | "rent" | "neutral";
export type DataSource = "city" | "country" | "global";

export interface LocationOut {
  display_name: string;
  lat: number;
  lon: number;
  country: string;
  country_code: string;
  city: string | null;
}

export interface AssumptionsOut {
  area_sqm: number;
  home_price: number;
  monthly_rent: number;
  horizon_years: number;
  down_payment_pct: number;
  mortgage_rate: number;
  loan_term_years: number;
  property_tax_rate: number;
  maintenance_rate: number;
  home_appreciation: number;
  rent_growth: number;
  investment_return: number;
  currency: string;
  data_source: DataSource;
}

export interface YearPointOut {
  year: number;
  buy_net_worth: number;
  rent_net_worth: number;
  home_value: number;
  loan_balance: number;
  home_equity: number;
}

export interface ResultOut {
  recommendation: Recommendation;
  horizon_years: number;
  buy_net_worth: number;
  rent_net_worth: number;
  advantage: number;
  advantage_pct: number;
  break_even_year: number | null;
  monthly_mortgage: number;
  total_buy_cost: number;
  total_rent_cost: number;
  timeline: YearPointOut[];
}

export interface AnalyzeResponse {
  location: LocationOut;
  assumptions: AssumptionsOut;
  result: ResultOut;
  summary: string;
}

export interface Overrides {
  area_sqm?: number;
  horizon_years?: number;
  home_price?: number;
  monthly_rent?: number;
  down_payment_pct?: number;
  mortgage_rate?: number;
  loan_term_years?: number;
  property_tax_rate?: number;
  maintenance_rate?: number;
  home_appreciation?: number;
  rent_growth?: number;
  investment_return?: number;
}
