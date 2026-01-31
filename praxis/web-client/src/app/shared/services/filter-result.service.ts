import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface FilterOption<T = unknown> {
    label: string;
    value: T;
    count?: number;
    disabled?: boolean;
    fullName?: string;
    icon?: string;
}

@Injectable({
    providedIn: 'root'
})
export class FilterResultService {

    /**
     * Computes availability of options based on current data and other applied filters.
     * 
     * @param items The dataset to filter against.
     * @param filterFn A function that returns true if an item matches the given value.
     * @param options The list of options to compute counts for.
     * @param currentSelected The currently selected values for this filter axis.
     * @param isMultiSelect Whether this filter axis supports multiple selection.
     */
    computeOptionMetrics<T, V>(
        items: T[],
        filterFn: (item: T, value: V) => boolean,
        options: FilterOption<V>[],
        currentSelected: V | V[] | null = null,
        isMultiSelect: boolean = false
    ): FilterOption<V>[] {
        return options.map(option => {
            let matches: number;

            if (isMultiSelect) {
                const SELECTED_ARRAY = Array.isArray(currentSelected) ? currentSelected : [];
                const IS_SELECTED = SELECTED_ARRAY.includes(option.value);

                // If already selected, "toggling" it means unselecting it.
                // However, usually we want to know what happens if we ADD it if it's not selected.
                // Or if it IS selected, how many items match it specifically in the context of other filters.
                // The requirement says "how many results if this filter is toggled".

                // For multi-select, selecting an option usually REPLACES the current selection for THAT axis 
                // in the context of showing "what would happen if I chose ONLY this or ADDED this".
                // Actually, the most intuitive count for a chip is "how many items match this option 
                // GIVEN all OTHER filter axes are applied".

                matches = items.filter(item => filterFn(item, option.value)).length;
            } else {
                matches = items.filter(item => filterFn(item, option.value)).length;
            }

            return {
                ...option,
                count: matches,
                disabled: matches === 0
            };
        });
    }
}
