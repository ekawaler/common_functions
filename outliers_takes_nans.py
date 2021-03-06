from __future__ import division
import pandas as pd
import numpy as np
import scipy.stats
import argparse

def fileToList(group_list):
    group = []
    with open(group_list, 'r') as fh:
        for line in fh.readlines():
            group.append(line.strip())
    return group

def cleanDF(df, sample_columns):
    '''
    Convert string nans to np.nan and string numbers to floats.
    '''
    df = df.replace(['na', 'NaN', 'Na', 'nan'], np.nan)
    df[sample_columns] = df[sample_columns].astype(float)

    return df

def convertToOutliers(df, gene_column_name, sample_columns, NUM_IQRs, up_or_down):
    '''
    Calculates the median, and inter-quartile range for each row/isoform.
    Inter-quartile range is defined as the value difference between the 25th and 75th percentile.
    Here, NaNs are ignored for each row, therefore a different number of values may be used for each row.

    '''
    df['row_iqr'] = scipy.stats.iqr(df[sample_columns], axis=1, nan_policy='omit')
    df['row_median'] = np.nanquantile(df[sample_columns], q=0.5, axis=1)

    outlier_df = pd.DataFrame()
    outlier_df[gene_column_name] = df[gene_column_name]

    if up_or_down == 'up':
        df['row_medPlus'] = (df['row_median'] + (NUM_IQRs*df['row_iqr']))
        for col in sample_columns:
            outlier_df[col] = (df[col] > df['row_medPlus']).astype(int)

    elif up_or_down == 'down':
        df['row_medMinus'] = (df['row_median'] - (NUM_IQRs*df['row_iqr']))
        for col in sample_columns:
            outlier_df[col] = (df[col] < df['row_medMinus']).astype(int)

    outlier_df[df[sample_columns].isnull()] = np.nan

    return outlier_df


def countNonNans(df, gene_column_name, sample_columns):
    not_outlier_cols = [x + '_notOutliers' for x in sample_columns]
    outlier_cols = [x + '_outliers' for x in sample_columns]

    agged_outliers = pd.DataFrame()
    agged_outliers[not_outlier_cols] = df.groupby(by=gene_column_name)[sample_columns].agg(lambda x: pd.Series(x==0).sum())
    agged_outliers[outlier_cols] = df.groupby(by=gene_column_name)[sample_columns].agg(lambda x: pd.Series(x==1).sum())
    agged_outliers = agged_outliers.reset_index()

    return agged_outliers

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Parse some arguments")
    parser.add_argument('--input_df', type=str)
    parser.add_argument('--iqrs_over_median', type=float, default=1.5)
    parser.add_argument('--gene_column_name', type=str, default='id')
    parser.add_argument('--output_file', type=str, default='outliers.tsv')
    parser.add_argument('--sample_names_file', type=str, default='sample_roster.txt')
    parser.add_argument('--up_or_down', type=str, choices=['up', 'down'], default='up')

    args = parser.parse_args()

    data_input = args.input_df
    gene_column_name = args.gene_column_name
    write_results_to = args.output_file
    NUM_IQRs = args.iqrs_over_median
    sample_names = args.sample_names_file
    up_or_down = args.up_or_down

    sample_columns = fileToList(sample_names)

    sample_data = pd.read_csv(data_input, sep='\t')
    sample_data = cleanDF(sample_data, sample_columns)

    outliers = convertToOutliers(sample_data, gene_column_name, sample_columns, NUM_IQRs, up_or_down)
    outliers = countNonNans(outliers, gene_column_name, sample_columns)
    outliers.to_csv(write_results_to, sep='\t', index=False)

    print('Outlier analysis complete. Results are in %s' %write_results_to)
