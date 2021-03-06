import numpy as np
from tqdm import tqdm

from scorers.constants import class_pattern, method_pattern


def get_comments(issue, username):
    comment_pages = issue.get_comments()
    num_comments = 0
    comments_date = []
    comments_length = []
    reactions = []
    contains_sample = []
    for comment in comment_pages:
        commenter = comment.user.login
        if commenter == username:
            comment_body = comment.body
            if comment_body is None:
                continue
            else:
                num_comments += 1
                containts_sample_code = (class_pattern.match(comment_body) is not None) or (method_pattern.match(comment_body) is not None)
                comments_date.append(comment.created_at)
                reactions.append(comment.get_reactions().totalCount)
                comments_length.append(len(comment_body.split()))
                contains_sample.append(containts_sample_code)
    return num_comments, comments_date, reactions, comments_length, contains_sample


def get_comments_score(g, username):
    issues = g.search_issues('language:Java commenter:{} -author:{} state:closed closed:>2019-01-01'.format(username, username),
                             sort='comments')
    scores = []
    for issue in tqdm(issues, total=issues.totalCount):
        num_comments, comments_dates, reactions, comments_length, contains_sample = get_comments(issue, username)
        issue_close_date = issue.closed_at
        issue_time_open = (issue_close_date - issue.created_at).days
        time_to_closing = [(issue_close_date - cd).days for cd in comments_dates]

        contains_sample_weight = np.array(contains_sample, dtype='float')
        contains_sample_weight[contains_sample_weight == 0] = 0.9
        contains_sample_weight[contains_sample_weight == 1] = 1

        comment_len_weight = np.array(comments_length, dtype='float')
        comment_len_weight[comment_len_weight < 10] = 0.5
        comment_len_weight[comment_len_weight >= 10] = 1

        time_weight = np.array(time_to_closing, dtype='int')
        time_weight[time_weight < 0] = 0
        time_weight[time_weight > 0] = 1

        time_to_closing = np.array(time_to_closing, dtype='float')
        if issue_time_open == 0:
            ttc_to = 1
        else:
            ttc_to = time_to_closing / issue_time_open

        score_ = contains_sample_weight * comment_len_weight * time_weight * ttc_to
        scores.append(score_)

    try:
        scores = np.concatenate(scores)
        scores = scores[scores != 0]
        if scores.shape[0] == 0:
            score = scores[0]
        else:
            score = scores.mean()
    except Exception:  # TODO narrow down - ZeroDivisionError, ValueError
        score = 0

    if np.isnan(score):
        score = 0

    return score
