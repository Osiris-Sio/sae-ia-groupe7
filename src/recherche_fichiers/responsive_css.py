RESPONSIVE_CSS = """
.search-layout {
    align-items: flex-start;
    flex-wrap: wrap !important;
}
.search-layout > .search-query {
    flex: 2 1 420px;
    min-width: 0 !important;
}
.search-layout > .search-options {
    flex: 1 1 320px;
    min-width: 0 !important;
}
.results-output,
.results-output * {
    min-width: 0;
}
.results-output .results-table {
    overflow-wrap: anywhere;
}
@media (max-width: 768px) {
    .search-layout > .search-query,
    .search-layout > .search-options {
        flex-basis: 100%;
    }
}
@media (max-width: 640px) {
    .gradio-container h1 {
        font-size: 1.6rem !important;
        line-height: 1.25;
    }
    .results-output .results-scroll {
        overflow-x: visible !important;
    }
    .results-output .results-table,
    .results-output .results-table tbody {
        display: block;
        width: 100%;
    }
    .results-output .results-table thead {
        display: none;
    }
    .results-output .results-table tr {
        display: block;
        margin-bottom: 12px;
        padding: 6px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
    }
    .results-output .results-table td {
        display: grid;
        grid-template-columns: minmax(5rem, 0.4fr) minmax(0, 1fr);
        gap: 8px;
        width: auto !important;
        padding: 8px 4px;
        overflow-wrap: anywhere;
    }
    .results-output .results-table td::before {
        content: attr(data-label);
        font-weight: 600;
    }
    .results-output .results-table td:not([data-label])::before {
        content: none;
    }
    .results-output .results-table td:last-child {
        display: block;
    }
    .results-output .results-table td:last-child::before {
        display: block;
        margin-bottom: 6px;
    }
}
"""