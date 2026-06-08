export type SortKey = "relevance" | "citations" | "recency";

export interface SearchResultItem {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published: string;
  url: string;
  citation_count: number;
  citation_data_missing: boolean;
}

export interface SearchResponse {
  search_id: string;
  results: SearchResultItem[];
  pool_size: number;
  warnings: string[];
}

export interface ResortResponse {
  search_id: string;
  results: SearchResultItem[];
  warnings: string[];
}
