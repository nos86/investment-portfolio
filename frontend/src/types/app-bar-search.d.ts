declare module '@db/app-bar-search/types' {
  export interface SearchResultItem {
    title: string
    url: string
    icon?: string
    children?: SearchResultItem[]
  }

  export type SearchResults = SearchResultItem
}
