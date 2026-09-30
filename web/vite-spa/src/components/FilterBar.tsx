// 通用筛选条（搜索 + 多维度筛选 + 排序）
import { Search, Filter } from 'lucide-react';

interface FilterOption {
  label: string;
  value: string;
  count?: number;
}

interface FilterBarProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (v: string) => void;
  filters?: { label: string; options: FilterOption[]; value: string; onChange: (v: string) => void }[];
  sortOptions?: FilterOption[];
  onSortChange?: (v: string) => void;
}

export function FilterBar({
  searchPlaceholder = '搜索...',
  searchValue = '',
  onSearchChange,
  filters = [],
  sortOptions = [],
  onSortChange,
}: FilterBarProps) {
  return (
    <div className="bg-card rounded-lg border border-gray-200 p-4 mb-4">
      <div className="flex flex-wrap items-center gap-3">
        {/* 搜索 */}
        <div className="flex-1 min-w-[200px] relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
          />
        </div>

        {/* 筛选 */}
        {filters.length > 0 && (
          <div className="flex items-center gap-2 text-sm">
            <Filter className="w-4 h-4 text-gray-400" />
            {filters.map((f) => (
              <select
                key={f.label}
                value={f.value}
                onChange={(e) => f.onChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md bg-card"
              >
                {f.options.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                    {o.count !== undefined && ` (${o.count})`}
                  </option>
                ))}
              </select>
            ))}
          </div>
        )}

        {/* 排序 */}
        {sortOptions.length > 0 && (
          <select
            onChange={(e) => onSortChange?.(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md bg-card text-sm"
          >
            {sortOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
