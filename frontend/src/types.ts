export interface Weights {
  relevance: number;
  citations: number;
  recency: number;
}

export interface SubScores {
  relevance: number;
  citations: number;
  recency: number;
}

export interface SearchResultItem {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published: string;
  url: string;
  citation_count: number;
  sub_scores: SubScores;
  final_score: number;
  citation_data_missing: boolean;
}

export interface SearchResponse {
  search_id: string;
  results: SearchResultItem[];
  pool_size: number;
  warnings: string[];
}
