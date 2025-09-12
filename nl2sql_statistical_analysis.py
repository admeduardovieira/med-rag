import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations
import os

def load_results_data():
    """Load the detailed NL2SQL results data"""
    try:
        df = pd.read_excel("output/results_questions_v2_100.xlsx")
        print(f"Loaded detailed results with {len(df)} rows")
        return df
    except Exception as e:
        print(f"Error loading results: {e}")
        return None

def load_summary_data():
    """Load the summary data for reference"""
    try:
        df = pd.read_excel("output/summary_questions_v2_100.xlsx")
        print(f"Loaded summary data with {len(df)} rows")
        return df
    except Exception as e:
        print(f"Error loading summary: {e}")
        return None

def perform_pairwise_ttests(df):
    """Perform pairwise t-tests between all model pairs"""
    # Get unique models
    models = sorted(df['model'].unique())
    print(f"Found {len(models)} models: {models}")

    # Create a matrix to store results
    results = {}
    ttest_results = []

    # Group by observation_id and model to get accuracy per query per model
    pivot_df = df.pivot_table(
        index='observation_id',
        columns='model',
        values='is_correct',
        aggfunc='first'  # Take first result if multiple runs
    )

    print(f"Pivot table shape: {pivot_df.shape}")

    # Perform pairwise t-tests
    for model1, model2 in combinations(models, 2):
        if model1 in pivot_df.columns and model2 in pivot_df.columns:
            # Get the boolean accuracy values for both models
            acc1 = pivot_df[model1].dropna()
            acc2 = pivot_df[model2].dropna()

            # Only compare queries that both models answered
            common_queries = acc1.index.intersection(acc2.index)
            if len(common_queries) < 10:  # Need minimum sample size
                print(f"Warning: Only {len(common_queries)} common queries for {model1} vs {model2}")
                continue

            acc1_common = acc1.loc[common_queries].astype(int)
            acc2_common = acc2.loc[common_queries].astype(int)

            # Perform t-test
            t_stat, p_value = stats.ttest_ind(acc1_common, acc2_common)

            # Calculate means
            mean1 = acc1_common.mean()
            mean2 = acc2_common.mean()

            ttest_results.append({
                'model1': model1,
                'model2': model2,
                'mean1': mean1,
                'mean2': mean2,
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'better_model': model1 if mean1 > mean2 else model2,
                'worse_model': model2 if mean1 > mean2 else model1,
                'mean_diff': abs(mean1 - mean2),
                'sample_size': len(common_queries)
            })

    return pd.DataFrame(ttest_results), pivot_df

def create_performance_matrix(ttest_df, models):
    """Create a performance comparison matrix showing wins/ties/losses"""
    # Initialize matrix with proper dtype
    n = len(models)
    performance_matrix = pd.DataFrame(0.0, index=models, columns=models, dtype=float)

    # Fill the matrix based on t-test results
    for _, row in ttest_df.iterrows():
        model1, model2 = row['model1'], row['model2']

        if row['significant']:
            # Significant difference: better model gets +1, worse model gets -1
            better = row['better_model']
            worse = row['worse_model']
            performance_matrix.loc[better, worse] = 1   # Win
            performance_matrix.loc[worse, better] = -1  # Loss
        else:
            # No significant difference: both get 0 (tie)
            performance_matrix.loc[model1, model2] = 0
            performance_matrix.loc[model2, model1] = 0

    return performance_matrix

def create_win_matrix(ttest_df, models):
    """Create a matrix showing number of wins for each model"""
    win_counts = pd.Series(0, index=models, dtype=int)

    for _, row in ttest_df.iterrows():
        if row['significant']:
            better = row['better_model']
            win_counts[better] += 1

    return win_counts

def plot_performance_matrix(performance_matrix, title="LLM Performance Comparison Matrix"):
    """Plot the performance matrix as a heatmap"""
    plt.figure(figsize=(12, 10))

    # Create mask for upper triangle (since matrix is symmetric)
    mask = np.triu(np.ones_like(performance_matrix, dtype=bool))

    # Create custom colormap: red for losses (-1), white for ties (0), green for wins (1)
    cmap = sns.diverging_palette(10, 130, as_cmap=True)

    # Create heatmap
    sns.heatmap(performance_matrix,
                annot=True,
                fmt='.0f',
                cmap=cmap,
                mask=mask,
                square=True,
                center=0,
                cbar_kws={'label': 'Performance (-1=Loss, 0=Tie, +1=Win)'})

    plt.title(title, fontsize=16)
    plt.xlabel('vs Model', fontsize=12)
    plt.ylabel('Model', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()
    plt.savefig('figures/nl2sql_performance_matrix.pdf', bbox_inches='tight', dpi=300)
    plt.show()

def plot_win_counts(win_counts, title="Number of Significant Wins per Model"):
    """Plot the win counts as a bar chart"""
    plt.figure(figsize=(12, 6))

    # Sort by win count
    win_counts_sorted = win_counts.sort_values(ascending=True)

    bars = plt.barh(range(len(win_counts_sorted)), win_counts_sorted.values)
    plt.yticks(range(len(win_counts_sorted)), win_counts_sorted.index)
    plt.xlabel('Number of Significant Wins')
    plt.title(title)

    # Add value labels
    for i, (model, count) in enumerate(zip(win_counts_sorted.index, win_counts_sorted.values)):
        plt.text(count + 0.1, i, str(count), va='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig('figures/nl2sql_win_counts.pdf', bbox_inches='tight', dpi=300)
    plt.show()

def analyze_results():
    """Main analysis function"""
    print("Starting NL2SQL statistical analysis...")

    # Load data
    df = load_results_data()
    summary_df = load_summary_data()

    if df is None or summary_df is None:
        return

    print("\nSummary statistics:")
    print(summary_df[['model', 'acc_mean', 'acc_stdvar', 'num_observations']].round(3))

    # Perform t-tests
    print("\nPerforming pairwise t-tests...")
    ttest_df, pivot_df = perform_pairwise_ttests(df)

    if ttest_df.empty:
        print("No valid t-test results found!")
        return

    print(f"\nCompleted {len(ttest_df)} pairwise comparisons")

    # Show significant differences
    significant = ttest_df[ttest_df['significant']].sort_values('p_value')
    print(f"\nSignificant differences found: {len(significant)}")
    if not significant.empty:
        print(significant[['model1', 'model2', 'mean1', 'mean2', 'p_value', 'better_model']].round(4))

    # Create performance matrix and win counts
    models = sorted(df['model'].unique())
    performance_matrix = create_performance_matrix(ttest_df, models)
    win_counts = create_win_matrix(ttest_df, models)

    print("\nPerformance Matrix (-1=Loss, 0=Tie, +1=Win in significant comparisons):")
    print(performance_matrix.round(0))

    print("\nWin Counts (number of significant victories):")
    print(win_counts.sort_values(ascending=False))

    # Plot matrices
    plot_performance_matrix(performance_matrix)
    plot_win_counts(win_counts)

    # Save results
    os.makedirs('output/analysis', exist_ok=True)
    ttest_df.to_csv('output/analysis/nl2sql_ttest_results.csv', index=False)
    performance_matrix.to_csv('output/analysis/nl2sql_performance_matrix.csv')
    win_counts.to_csv('output/analysis/nl2sql_win_counts.csv', header=['wins'])

    print("\nResults saved to output/analysis/")

    # Summary statistics
    total_comparisons = len(ttest_df)
    significant_comparisons = len(ttest_df[ttest_df['significant']])
    print(f"\nSummary:")
    print(f"- Total pairwise comparisons: {total_comparisons}")
    print(f"- Significant differences: {significant_comparisons} ({100*significant_comparisons/total_comparisons:.1f}%)")
    print(f"- Average accuracy range: {summary_df['acc_mean'].min():.3f} - {summary_df['acc_mean'].max():.3f}")

if __name__ == "__main__":
    analyze_results()
