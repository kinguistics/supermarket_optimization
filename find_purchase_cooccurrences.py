import csv
import argparse
from itertools import combinations

# testing
import time
import random


# how frequent should co-occurrences be for us to include them?
SIGMA = 4

# what's the smallest size of a frequent item set?
MIN_SET_SIZE = 3

# a parameter for tuning the time/space tradeoff for verifying large subsets
# haven't had a chance to test it
#MAX_COMBO_SIZE = 1000

'''
FUNCTIONS FOR PARSING THE INPUT FILE
'''
def parse_retail_data(filename):
    """Parse retail transaction data.
    
    Args:
        filename (str) : the name of the file where the data can be found
    Returns:
        list(list(int)) containing all purchase data
    """
    all_purchases = []
    
    with open(filename) as f:
        f_reader = csv.reader(f, delimiter=' ')
        
        for purchase_line in f_reader:
            items_purchased = parse_purchase(purchase_line)
            all_purchases.append(items_purchased)
    
    return all_purchases
                
def parse_purchase(purchase_line):
    """Parse a single line of purchase data.
    
    Args:
        purchase_line (list(str)) : the split line from the transaction file
    
    Returns:
        list(int) : the cleaned-up single line
    """
    items_purchased = [int(v) for v in purchase_line if v!='']

    # make unique so we don't count multiple purchases of the same product
    items_purchased = list(set(items_purchased))    
    
    # sort so we can always have subsets in the same order
    items_purchased.sort()
    
    return items_purchased

'''
FUNCTIONS FOR COUNTING ITEMS AND SUBSETS
'''
def count_size_one_subsets(all_purchases):
    """Count all subsets of size 1 in the purchases list.
    
    This is the base step for the inductive process of finding interesting 
    subsets of items.
    
    Args:
        all_purchases (list(list(int)) : a list of purchase lists
    
    Returns:
        dict(int : dict(frozenset : list(int)) : 
            A dictionary with one key (1), which points to a dict.
            The inner dict maps a set of items to a list of indices corresponding
            to purchases that that set of items is found in.
    """
    subset_size = 1
    
    subsets_indices = {}
    subsets_indices[subset_size] = {}
    
    for purchase_idx in range(len(all_purchases)):
        purchase = all_purchases[purchase_idx]
        
        for item in purchase:
            # store it as a frozenset so it's both unordered and immutable
            item_key = frozenset([item])
            
            if item_key not in subsets_indices[subset_size]:
                subsets_indices[subset_size][item_key] = []
            subsets_indices[subset_size][item_key].append(purchase_idx)
    
    return subsets_indices

def count_subsets_of_size(all_purchases, subset_size, subsets_indices):
    """Counts all potentially interesting subsets of a certain size.
    
    The inductive step of the algorithm, this takes the dictionary containing
    all interesting subsets of cardinality < subset_size. It uses
    this dict and the all_purchases to construct all possible supersets from
    the sets of cardinality subset_size-1 and of cardinality 1. 
    
    It then checks every* subset of the constructed superset to see if it's 
    interesting. If all of the subsets are interesting, then the constructed 
    superset can be considered potentially interesting, and its purchase
    is added to the indices dictionary. We check in the pruning step to see
    if it's actually interesting.
    
    (* - well, potentially every subset. see the note about MAX_COMBO_SIZE)
    
    Args:
        all_purchases (list(list(int)) : the list of purchase lists
        subset_size (int) : the cardinality of the sets we're constructing at this step
        subsets_indices dict(int : dict(frozenset : list(int))) :
            a dict that maps a subset size to a dict whose keys are interesting
            subsets of that size, and whose values are lists of the purchase
            indices where each interesting subset was purchased
    
    Returns:
        subsets_indices dict(int : dict(frozenset : list(int))) :
            an updated indices dict that now includes potentially (i.e., unpruned)
            subsets of cardinality subset_size.
    """
    # initialize the new dict
    subsets_indices[subset_size] = {}
    
    # grab the subsets of size n-1
    n_minus_one_indices = subsets_indices[subset_size-1]
    
    # construct new subsets of size n from the sets of size n-1 and size 1
    for subset in n_minus_one_indices:
        purchase_indices = n_minus_one_indices[subset]
        
        # go through each purchase that this item was purchased in
        for purchase_idx in purchase_indices:
            current_purchase = all_purchases[purchase_idx]

            # go through everything else in this purchase
            for item in current_purchase:
                item_key = frozenset([item])
                
                # make sure we're not doubling up items
                if item in subset:
                    continue
                
                # skip any individual item that isn't frequent enough
                if item_key not in subsets_indices[1]:
                    continue
                
                # create a new superset
                # (need to cast back and forth from set() to add a new item)
                this_subset_as_set = set(subset)
                this_subset_as_set.add(item)
                superset = frozenset(this_subset_as_set)
                
                # if it already exists, we don't need to check it
                if superset in subsets_indices[subset_size]:
                    # add this purchase if it's not already in there
                    if purchase_idx not in subsets_indices[subset_size][superset]:
                        subsets_indices[subset_size][superset].append(purchase_idx)
                    continue
                
                '''
                Now, we check each subset of the constructed superset
                (i.e., every subset from size 2 to the size of the constructed
                superset).
                
                This grows very fast (2^n), so the MAX_COMBO_SIZE global constant
                can be used to only check subsets up to size MAX_COMBO_SIZE
                (or the size of the current subset, whichever is smaller).
                If the constructed superset passes those checks, its indices
                will get logged, potentially taking up more space than needed,
                but saving time by not checking larger subsets.
                
                I keep this very high to minimize memory usage, but it might be
                worth playing around with.
                '''
                superset_potentially_good = True
                max_combo_size = min(MAX_COMBO_SIZE, subset_size)
                
                # check subsets of every size
                for combo_size in range(2, max_combo_size):
                    for sub_superset_tuple in combinations(superset, combo_size):
                        sub_superset = frozenset(sub_superset_tuple)
                        
                        # if the subset hasn't been logged, then it wasn't frequent enough
                        # so the current superset can never be frequent enough
                        if sub_superset not in subsets_indices[combo_size]:
                            superset_potentially_good = False
                            break
                    
                    # are we here because we broke out of the inner loop?
                    # if so, then this superset can never be good        
                    if not superset_potentially_good:
                        break
                        
                if superset_potentially_good:
                    if superset not in subsets_indices[subset_size]:
                        subsets_indices[subset_size][superset] = []
                    subsets_indices[subset_size][superset].append(purchase_idx)
    
    return subsets_indices

def prune_subsets(subsets_indices):
    """Prune subsets that are less frequent than SIGMA.
    (Specifically, prune the subsets of the largest size in the dict)
    Do this in place, so we don't return.
    
    Args:
        subsets_indices (dict(int : dict(frozenset : list(int))) :
            mapping of set sizes to mapping of sets to their purchase indices
    """
        
    size = max(subsets_indices.keys())
    
    for subset in subsets_indices[size].keys():
        this_subset_indices = subsets_indices[size][subset]
        if len(this_subset_indices) < SIGMA:
            del subsets_indices[size][subset]

if __name__ == "__main__":
    '''
    PARSE COMMAND-LINE ARGUMENTS
    '''
    arg_parser = argparse.ArgumentParser(description="Find frequently co-purchased items in supermarker checkout data.")
    
    # find the file name
    arg_parser.add_argument('filename', 
                            metavar='input_file', 
                            type=str,
                            help="A file with one purchase per line, where each line is a space-separated list of PLU values")
    
    # find sigma (defaults to 4)
    arg_parser.add_argument('--sigma',
                            metavar='sigma',
                            type=int,
                            default=SIGMA,
                            help="The minimum number of times a set of items must co-occur")
    
    # offer a choice of output filename (defaults to <input_filename>_<sigma>.csv)
    arg_parser.add_argument('--output_filename',
                            metavar='output_filename',
                            type=str,
                            default=None,
                            help="The output file name (defaults to <input_filename>_<sigma>.csv)")
    
    # optionally change the size of the smallest subset to log
    arg_parser.add_argument('--min_set_size',
                            metavar="min_set_size",
                            type=int,
                            default=MIN_SET_SIZE,
                            help="the size of the smallest sets to write to the output file")
                                                        
    # get the arguments
    args = arg_parser.parse_args()
    filename = args.filename
    sigma = args.sigma

    # check if we're using the default output filename
    output_filename = args.output_filename
    if output_filename is None:
        output_filename = '%s_sigma%s.csv' % ('.'.join(filename.split('.')[:-1]),
                                         sigma)
    
    '''
    FIND THE FREQUENTLY OCCURRING ITEM SETS
    
    The algorithm takes advantage of the fact that every set of items of size
    n with frequency c must have a strict subset of size n-1 with frequency >= c
    
    In other words, if a particular set s of size 2 only occurs 3 times in the
    purchase history, then any set of size 3 that includes s can occur no more
    than 3 times. We can thus ignore any larger set that includes s.
    
    It uses this fact by first constructing every subset of size n = 1, 
    removing those sets with frequency < SIGMA, and only considering supersets
    of the remaining sets.
    
    For each superset, it checks all subsets to see if they have frequency >= SIGMA.
    (Since the space of interesting subsets grows more and more sparse as the
    subset size increases, and the algorithm immediately breaks out of the search
    when it finds an uninteresting subset, this results in relatively few total 
    searches of this space)
    
    Once we find all potentially interesting supersets of a given size, we
    run through and check their counts, pruning those that aren't frequent enough.
    
    '''

    # parse the data
    all_purchases = parse_retail_data(filename)
    max_purchase_size = max([len(purchase) for purchase in all_purchases])

    log_fname = 'optimize_combo_size_by_time.csv'
    with open(log_fname,'w', buffering=1) as log_fout:
        log_fwriter = csv.writer(log_fout)
        log_header_out = ['iteration','max_combo_size.train','total_time.train','n_subset_candidates.train','n_subsets_continued.train', 'max_combo_size.test','total_time.test','n_subset_candidates.test','n_subsets_continued.test']
        log_fwriter.writerow(log_header_out)
        
        N_OPT_ITERATIONS = 100
        
        for iteration in range(N_OPT_ITERATIONS):
            random.shuffle(all_purchases)
            train_purchases = all_purchases[:len(all_purchases)/2]
            test_purchases = all_purchases[len(all_purchases)/2:]
            
            train_rowsout = []
            
            time_by_size = {}
            
            # the maximum set size is 14, so I'm going to use that to try to fit the
            #   max_combo_size parameter
            for MAX_COMBO_SIZE in reversed(range(2,15)):
                # time is obviously time
                start_time = time.time()
                # the number of subsets we ever store to be moved onto the next step
                subsets_considered = 0
                # the number of subsets that gets moved to the next step
                subsets_continued = 0
                
                '''
                base step -- get the subsets of size 1
                '''
                subsets_indices = count_size_one_subsets(train_purchases)
                subsets_considered += len(subsets_indices[1])
                prune_subsets(subsets_indices)
                subsets_continued += len(subsets_indices[1])
                
                print "starting with",len(subsets_indices[1])
            
                # gradually increase the size of sets
                for subset_size in range(2, max_purchase_size):
                    print "checking subsets of size", subset_size
                    
                    '''
                    inductive step -- get the subsets of size n
                    '''
                    subsets_indices = count_subsets_of_size(train_purchases,
                                                            subset_size,
                                                            subsets_indices)
                    subsets_considered += len(subsets_indices[subset_size])
                    prune_subsets(subsets_indices)
                    subsets_continued += len(subsets_indices[subset_size])
                    
                    n_added = len(subsets_indices[subset_size])
                    print "added", n_added
            
                    # if we didn't add anything in the last round, we're done
                    if n_added == 0:
                        break               
                
                end_time = time.time()
                train_total_time = end_time - start_time
                
                rowout = [iteration, MAX_COMBO_SIZE, train_total_time, subsets_considered, subsets_continued]
                #log_fwriter.writerow(rowout)
                train_rowsout.append(rowout)
                
                time_by_size[MAX_COMBO_SIZE] = train_total_time
                
                print "iteration:", iteration, "; train max combo size:", MAX_COMBO_SIZE, "; time:", train_total_time
            
            # find optimal max_combo_size, for time
            all_times_by_sizes = time_by_size.items()
            all_times_by_sizes.sort(cmp=lambda x,y: cmp(x[1],y[1]))
            best_size = all_times_by_sizes[0][0]
            
            test_rowsout = []
            
            for MAX_COMBO_SIZE in reversed(range(2,15)):
            
                # time is obviously time
                start_time = time.time()
                # the number of subsets we ever store to be moved onto the next step
                subsets_considered = 0
                # the number of subsets that gets moved to the next step
                subsets_continued = 0
                
                '''
                base step -- get the subsets of size 1
                '''
                subsets_indices = count_size_one_subsets(test_purchases)
                subsets_considered += len(subsets_indices[1])
                prune_subsets(subsets_indices)
                subsets_continued += len(subsets_indices[1])
                
                print "starting with",len(subsets_indices[1])
            
                # gradually increase the size of sets
                for subset_size in range(2, max_purchase_size):
                    print "checking subsets of size", subset_size
                    
                    '''
                    inductive step -- get the subsets of size n
                    '''
                    subsets_indices = count_subsets_of_size(test_purchases,
                                                            subset_size,
                                                            subsets_indices)
                    subsets_considered += len(subsets_indices[subset_size])
                    prune_subsets(subsets_indices)
                    subsets_continued += len(subsets_indices[subset_size])
                    
                    n_added = len(subsets_indices[subset_size])
                    print "added", n_added
            
                    # if we didn't add anything in the last round, we're done
                    if n_added == 0:
                        break               
                
                end_time = time.time()
                test_total_time = end_time - start_time
                
                rowout = [MAX_COMBO_SIZE, test_total_time, subsets_considered, subsets_continued]
                test_rowsout.append(rowout)
                    
                print "iteration:", iteration, "; train max combo size:", MAX_COMBO_SIZE, "; time:", test_total_time

            assert len(test_rowsout) == len(train_rowsout)
            
            for rowout_idx in range(len(train_rowsout)):
                full_rowout = train_rowsout[rowout_idx] + test_rowsout[rowout_idx]
                log_fwriter.writerow(full_rowout)
                        
'''
    # write the interesting cooccurrences to the output file
    with open(output_filename,'w') as fout:
        fwriter = csv.writer(fout)
        for subset_size in subsets_indices:
            if subset_size < MIN_SET_SIZE:
                continue
            for subset in subsets_indices[subset_size]:
                purchase_indices = subsets_indices[subset_size][subset]
                frequency = len(purchase_indices)
                
                rowout = [subset_size, frequency] + list(subset)
                fwriter.writerow(rowout)
'''