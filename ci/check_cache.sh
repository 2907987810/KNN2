#!/bin/bash

if [ "$TRAVIS_PULL_REQUEST" == "false" ]
then
    echo "Not a PR: checking for changes in ci/ from last 2 commits"
    git diff HEAD~2 --numstat | grep -E "ci/"
    ci_changes=$(git diff HEAD~2 --numstat | grep -E "ci/"| wc -l)
else
    echo "PR: checking for changes in ci/ from last 2 commits"
    git diff FETCH_HEAD~2 --numstat | grep -E "ci/"
    ci_changes=$(git diff FETCH_HEAD~2 --numstat | grep -E "ci/"| wc -l)
fi

MINICONDA_DIR="$HOME/miniconda/"
CACHE_DIR="$HOME/.cache/"
CCACHE_DIR="$HOME/.ccache/"

if [ $ci_changes -ne 0 ]
then
    echo "Files have changed in ci/ deleting all caches"
    rm -rf "$MINICONDA_DIR"
    rm -rf "$CACHE_DIR"
    rm -rf "$CCACHE_DIR"
fi