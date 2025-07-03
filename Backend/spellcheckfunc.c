#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h> // For tolower
#include <stdbool.h> // For bool type (though using int for ctypes compatibility)
#include <math.h> // For abs and fmin

// Defines
#define MAX_WORD_LEN 50
#define MAX_LINE_LEN 256
#define DICTIONARY_SIZE 375000 // Approximate size, adjust if your dictionary is much larger
#define MAX_TEMP_SUGGESTIONS 1000 // This MUST match MAX_TEMP_SUGGESTIONS_C in Python!

// Struct to store dictionary words
typedef struct {
    char word[MAX_WORD_LEN];
} DictionaryWord;

// Struct for suggestions
typedef struct {
    char word[MAX_WORD_LEN];
    int dist; // Levenshtein distance
} Suggestion;

// Global dictionary (for simplicity, but can be passed around)
DictionaryWord* dictionary = NULL;
int dictionary_count = 0;
int dictionary_capacity = 0;

// Function Prototypes
int damerau_levenshtein_distance(const char *s1, const char *s2);
int load_dictionary(const char* filename);
int is_word_correct(const char* word);
int get_suggestions(const char* word, int tolerance, int misspelled_word_len, int length_tolerance, Suggestion* suggestions);
void sort_suggestions(Suggestion *suggestions, int count);
void cleanup();


// Function to calculate Damerau-Levenshtein distance (replaces previous levenshtein_distance)
// This implements the "restricted" Damerau-Levenshtein, which handles adjacent transpositions.
int damerau_levenshtein_distance(const char *s1, const char *s2) {
    int len1 = strlen(s1);
    int len2 = strlen(s2);

    if (len1 == 0) return len2;
    if (len2 == 0) return len1;

    // Allocate a 2D array (matrix) for dynamic programming
    // +1 for the empty string case (0-th row/column)
    int **dp = (int **)malloc((len1 + 1) * sizeof(int *));
    if (dp == NULL) {
        perror("Failed to allocate dp rows in damerau_levenshtein_distance");
        return -1; // Indicate error
    }
    for (int i = 0; i <= len1; i++) {
        dp[i] = (int *)malloc((len2 + 1) * sizeof(int));
        if (dp[i] == NULL) {
            perror("Failed to allocate dp columns in damerau_levenshtein_distance");
            // Free previously allocated rows
            for (int k = 0; k < i; k++) free(dp[k]);
            free(dp);
            return -1; // Indicate error
        }
    }

    // Initialize the first row and column
    for (int i = 0; i <= len1; i++) {
        dp[i][0] = i;
    }
    for (int j = 0; j <= len2; j++) {
        dp[0][j] = j;
    }

    // Fill the dp table
    for (int i = 1; i <= len1; i++) {
        for (int j = 1; j <= len2; j++) {
            int cost = (s1[i - 1] == s2[j - 1]) ? 0 : 1;

            // Levenshtein part (insertion, deletion, substitution/match)
            dp[i][j] = fmin(dp[i - 1][j] + 1,        // Deletion
                           fmin(dp[i][j - 1] + 1,    // Insertion
                                dp[i - 1][j - 1] + cost)); // Substitution or Match

            // Damerau-Levenshtein transposition part
            // Check for adjacent transposition (e.g., 'ab' vs 'ba')
            if (i > 1 && j > 1 && s1[i - 1] == s2[j - 2] && s1[i - 2] == s2[j - 1]) {
                dp[i][j] = fmin(dp[i][j], dp[i - 2][j - 2] + 1); // +1 for the transposition cost
            }
        }
    }

    int result = dp[len1][len2];

    // Free the allocated memory
    for (int i = 0; i <= len1; i++) {
        free(dp[i]);
    }
    free(dp);

    return result;
}

// Function to load dictionary from a file
// Returns 1 on success, 0 on failure
int load_dictionary(const char* filename) {
    cleanup(); // Clean up any previously loaded dictionary

    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        fprintf(stderr, "Error: Could not open dictionary file '%s'\n", filename);
        return 0; // Failure
    }

    dictionary_capacity = DICTIONARY_SIZE; // Initial capacity
    dictionary = (DictionaryWord*)malloc(dictionary_capacity * sizeof(DictionaryWord));
    if (dictionary == NULL) {
        perror("Failed to allocate dictionary memory");
        fclose(file);
        return 0; // Failure
    }

    char line[MAX_LINE_LEN];
    dictionary_count = 0;

    while (fgets(line, sizeof(line), file)) {
        // Remove newline and carriage return characters if present
        line[strcspn(line, "\n\r")] = 0;

        // Convert word to lowercase
        for (int i = 0; line[i]; i++) {
            line[i] = tolower((unsigned char)line[i]);
        }
        
        // --- DEBUG PRINT: Dictionary words being loaded ---
        // printf("Dict load: '%s' (len=%lu)\n", line, strlen(line)); // Commented out for less verbosity
        
        if (strlen(line) < MAX_WORD_LEN) { // Ensure word fits into buffer
            if (dictionary_count >= dictionary_capacity) {
                // Resize dictionary if needed
                dictionary_capacity *= 2;
                DictionaryWord* temp = (DictionaryWord*)realloc(dictionary, dictionary_capacity * sizeof(DictionaryWord));
                if (temp == NULL) {
                    perror("Failed to reallocate dictionary memory");
                    // Cleanup current dictionary before returning
                    free(dictionary);
                    dictionary = NULL;
                    dictionary_count = 0;
                    dictionary_capacity = 0;
                    fclose(file);
                    return 0; // Failure
                }
                dictionary = temp;
            }
            strncpy(dictionary[dictionary_count].word, line, MAX_WORD_LEN - 1); // Use strncpy for safety
            dictionary[dictionary_count].word[MAX_WORD_LEN - 1] = '\0'; // Ensure null termination
            dictionary_count++;
        } else {
             // printf("Dict load: SKIPPING too long word '%s' (len=%lu)\n", line, strlen(line)); // Commented out for less verbosity
        }
    }

    fclose(file);
    // --- DEBUG PRINT: Total words loaded ---
    printf("Dict load finished. Total words: %d\n", dictionary_count);
    return 1; // Success
}

// Function to check if a word is correct
// Returns 1 if correct, 0 if incorrect
int is_word_correct(const char* word) {
    if (dictionary == NULL || dictionary_count == 0) {
        printf("is_word_correct: Dictionary not loaded or empty.\n");
        return 0; // No dictionary loaded
    }

    char lower_word[MAX_WORD_LEN];
    strncpy(lower_word, word, MAX_WORD_LEN - 1);
    lower_word[MAX_WORD_LEN - 1] = '\0';
    for (int i = 0; lower_word[i]; i++) {
        lower_word[i] = tolower((unsigned char)lower_word[i]);
    }
    // --- DEBUG PRINT: Word received from Python ---
    printf("is_word_correct: Checking input word '%s' (len=%lu)\n", lower_word, strlen(lower_word));

    for (int i = 0; i < dictionary_count; i++) {
        if (strcmp(lower_word, dictionary[i].word) == 0) {
            // --- DEBUG PRINT: Match found ---
            printf("is_word_correct: MATCH FOUND for '%s' with dict word '%s'!\n", lower_word, dictionary[i].word);
            return 1; // Word found in dictionary
        }
    }
    // --- DEBUG PRINT: No match found ---
    printf("is_word_correct: NO MATCH found for '%s'.\n", lower_word);
    return 0; // Word not found
}


// Function to get spelling suggestions
// Fills the suggestions array and returns the number of suggestions found
int get_suggestions(const char* word, int tolerance, int misspelled_word_len, int length_tolerance, Suggestion* suggestions) {
    if (dictionary == NULL || dictionary_count == 0) {
        printf("get_suggestions: Dictionary not loaded or empty.\n");
        return 0; // No dictionary loaded
    }

    char lower_word[MAX_WORD_LEN];
    strncpy(lower_word, word, MAX_WORD_LEN - 1);
    lower_word[MAX_WORD_LEN - 1] = '\0';
    for (int i = 0; lower_word[i]; i++) {
        lower_word[i] = tolower((unsigned char)lower_word[i]);
    }
    printf("get_suggestions: For input word '%s' (len=%lu)\n", lower_word, strlen(lower_word));


    int suggestion_count = 0;

    for (int i = 0; i < dictionary_count; i++) {
        const char* dict_word = dictionary[i].word;
        int current_dict_word_len = strlen(dict_word);

        // Filter out words shorter than the misspelled word (as requested)
        if (current_dict_word_len < misspelled_word_len) {
            continue; // Skip this dictionary word
        }
        
        // Filter based on absolute length difference (max deviation allowed)
        if (abs(current_dict_word_len - misspelled_word_len) > length_tolerance) {
            continue; // Skip this dictionary word if its length difference is too high
        }

        int dist = damerau_levenshtein_distance(lower_word, dict_word);
        
        // --- VERBOSE DEBUG PRINT: SHOW DISTANCE FOR EACH WORD (THIS LINE IS UNCOMMENTED) ---
        printf("DEBUG_SUGG: Input '%s' (len=%lu) vs Dict '%s' (len=%lu) -> Dist: %d\n",
               lower_word, strlen(lower_word), dict_word, strlen(dict_word), dist);
        // --- END VERBOSE DEBUG PRINT ---


        if (dist >= 0 && dist <= tolerance) { // Check for valid distance and within tolerance
            if (suggestion_count < MAX_TEMP_SUGGESTIONS) {
            strncpy(suggestions[suggestion_count].word, dict_word, MAX_WORD_LEN - 1);
            suggestions[suggestion_count].word[MAX_WORD_LEN - 1] = '\0';
            suggestions[suggestion_count].dist = dist;
            suggestion_count++;
            } else {
                // If we hit the max temporary suggestions, we can stop early
                break;
            }
        }
    }
    
    // Call the sorting function to order suggestions by distance
    sort_suggestions(suggestions, suggestion_count);

    printf("get_suggestions: Found %d suggestions.\n", suggestion_count);
    return suggestion_count;
}

// Sorts suggestions by distance (ascending) then alphabetically by word
void sort_suggestions(Suggestion *suggestions, int count) {
    for (int i = 0; i < count - 1; i++) {
        for (int j = i + 1; j < count; j++) {
            if (suggestions[j].dist < suggestions[i].dist || 
                (suggestions[j].dist == suggestions[i].dist && strcmp(suggestions[j].word, suggestions[i].word) < 0)) {
                Suggestion temp = suggestions[i];
                suggestions[i] = suggestions[j];
                suggestions[j] = temp;
            }
        }
    }
}


// Function to free dictionary memory
void cleanup() {
    if (dictionary != NULL) {
        free(dictionary);
        dictionary = NULL;
    }
    dictionary_count = 0;
    dictionary_capacity = 0;
    printf("C cleanup: Dictionary memory freed.\n"); // Debug print for cleanup
}



int main() {
    const char* dict_file = "hi.txt"; // Make sure this file exists
    printf("Loading dictionary from: %s\n", dict_file);
    if (!load_dictionary(dict_file)) {
        printf("Failed to load dictionary.\n");
        return 1;
    }
    printf("Dictionary loaded with %d words.\n", dictionary_count);

    char test_word[MAX_WORD_LEN];

    printf("\n--- Spell Check Test ---\n");
    strcpy(test_word, "nayway");
    printf("Is '%s' correct? %s\n", test_word, is_word_correct(test_word) ? "Yes" : "No");
    printf("%d\n", damerau_levenshtein_distance("nayway","anyway"));
    
    Suggestion temp_suggestions[MAX_TEMP_SUGGESTIONS];
    int num_suggestions;

    
    num_suggestions = get_suggestions(test_word, 3, strlen(test_word), 2, temp_suggestions);
    for (int i = 0; i < 10; i++) {
        printf("  %s (dist: %d)\n", temp_suggestions[i].word, temp_suggestions[i].dist);
    }
    if (num_suggestions == 0) printf("  No suggestions found.\n");

    
    return 0;
}
