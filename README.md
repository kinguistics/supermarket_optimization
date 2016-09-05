# supermarket_optimization
A program that takes a list of transactions with PLU numbers, and produces a comma-separated file of frequently co-purchased items.

This repository contains the following files:
find_purchase_cooccurrences.py
	The Python code for actually finding the subsets
retail_25k.dat
	A list of 25k transactions
retail_25k_sigma4_setsize3.csv
	All subsets of size 3 or larger that occur more than 4 times in the transactions
README.md
	This file

To generate the output file from an input file, type:
    > python find_purchase_cooccurrences.py <input_file>
where the input file is a space-separated values file containing lists of transactions.

The program takes the following optional inputs:
	--sigma <sigma> 
		The number of times a subset of items must have been purchased together in order
		for it to be considered "frequent"
		Defaults to 4
	--min_set_size <min_set_size>
		The minimum number of items contained in a frequent subset
		Defaults to 3
	--output_filename <output_filename>
		The name of the file to write the frequent subsets to
		Defaults to <input_file>_sigma<sigma>_setsize<min_set_size>.csv

The program prints out its progress as it inductively builds subsets. It takes between
8 and 10 minutes to run on my machine.


Algorithm:
The algorithm works inductively. The base step creates a collection of indices where every
subset of size 1 occurs.

The inductive step examines each subset of size n, and creates candidate supersets by
going to each transaction where the subset was purchased, and forming the union of the subset
with every other item purchased in those transactions, one by one.

Candidate subsets of size n that do not occur at least as frequently as <sigma> are
pruned after each step.

The inductive step includes a subroutine that checks each subset of a candidate superset
to make sure every subset occurs at least <sigma> times, and removes the candidate
superset from consideration if it does not meet this requirement (since any superset of
a subset with frequency f can occur at most f times). The code includes a parameter,
MAX_COMBO_SIZE, that determines the maximum subset size to test each candidate superset on,
since testing every subset of a superset of size n takes 2^n time, and most candidate
supersets are discarded fairly early on anyway. Optimizing this parameter for time revealed
that the code runs fastest when the parameter is set to 3 (but the slowest value of this parameter
only increases the time by about 10%).