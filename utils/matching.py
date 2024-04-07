from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz, process
from typing import List


def match_multiple_columns(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    columns1: List[str],
    columns2: List[str],
    threshold: float = 80.0,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Matches specified columns between two pandas DataFrames using RapidFuzz based on string similarity,
    and returns full rows from both DataFrames for each match.

    Parameters:
    - df1, df2: DataFrames containing the columns to be matched.
    - columns1: List of column names in df1 to match.
    - columns2: List of column names in df2 to match against.
    - threshold: Similarity score threshold (0-100) to consider a match.
    - limit: Maximum number of matches to return for each value in columns1.

    Returns:
    - A DataFrame combining full rows from both df1 and df2 for each match, with additional columns for
      match details ('matched_column', 'similarity_score').
    """
    if len(columns1) != len(columns2):
        raise ValueError('columns1 and columns2 must have the same length.')

    # Collecting match details along with the indices of matched rows.
    matches_detail = []

    for col1, col2 in zip(columns1, columns2):
        unique_vals2 = df2[col2].unique().tolist()

        unique_vals2 = [
            str(val)
            for val in unique_vals2
            if not pd.isnull(val) and val != 'N/A'
        ]

        for idx1, value in df1[col1].items():
            if pd.isnull(value) or value == 'N/A':
                continue

            matches = process.extract(
                value,
                unique_vals2,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold,
                limit=limit,
            )
            for matched_value, score, idx2 in matches:
                # Append match details along with the indices of matched rows.
                matches_detail.append(
                    (
                        idx1,
                        df2[df2[col2] == matched_value].index[0],
                        col1,
                        matched_value,
                        score,
                    )
                )

    # Generating the combined DataFrame.
    combined_rows = []
    for idx1, idx2, matched_column, matched_value, score in matches_detail:
        row1 = df1.loc[idx1].to_dict()
        row2 = df2.loc[idx2].to_dict()

        # compare the brand names
        brand_score = fuzz.token_sort_ratio(
            row1['brand_name'], row2['brand_name']
        )
        if brand_score < 40:
            continue

        # Combining data from both rows with match details.
        coup_row = {
            **row1,
            'matched_column': matched_column,
            'matched_value': matched_value,
            'similarity_score': score,
            'matched_row_index': f'{idx1}, {idx2}',
        }

        sale_row = {
            **row2,
            'matched_column': matched_column,
            'matched_value': matched_value,
            'similarity_score': score,
            'matched_row_index': f'{idx1}, {idx2}',
        }

        combined_rows.append(coup_row)
        combined_rows.append(sale_row)

    # Grouping the combined rows by the index of their corresponding matched row index.
    matches_df = pd.DataFrame(combined_rows)

    if matches_df.empty:
        return matches_df

    matches_df = matches_df.groupby('matched_row_index').apply(
        lambda x: x.reset_index(drop=True)
    )

    return matches_df
