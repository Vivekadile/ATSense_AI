from backend import experience


def test_explicit_years_phrase():
    assert experience.estimate_years_experience("7+ years of experience in backend") == 7.0
    assert experience.estimate_years_experience("3 yrs experience") == 3.0


def test_date_range_to_present():
    text = "Software Engineer, 2019 - Present\nIntern, 2018 to 2019"
    years = experience.estimate_years_experience(text)
    assert years >= 6  # 2019->now (>=6 as of 2025+) plus a 1-year intern span


def test_no_signal_returns_zero():
    assert experience.estimate_years_experience("Enthusiastic new graduate") == 0.0


def test_education_level_detection():
    assert experience.detect_education_level("PhD in Computer Science") == 5
    assert experience.detect_education_level("Bachelor of Engineering") == 3
    assert experience.detect_education_level("No degree listed") == 0


def test_required_years_from_job_takes_minimum():
    # multiple explicit "N years experience" phrases -> the smallest wins
    jd = "Minimum 3 years of experience required. 5 years experience preferred."
    assert experience.required_years_from_job(jd) == 3.0


def test_everyday_words_are_not_degrees():
    jd = "You will be building APIs. Our Scrum Master and Associate Engineer support you."
    assert experience.detect_education_level(jd) == 0


def test_degree_abbreviations():
    assert experience.detect_education_level("B.E. in Mechanical Engineering") == 3
    assert experience.detect_education_level("B.Tech, Computer Science") == 3
    assert experience.detect_education_level("M.S. in Data Science") == 4
    assert experience.detect_education_level("Master's degree preferred") == 4
    assert experience.detect_education_level("Associate degree in IT") == 2


def test_education_dates_not_counted_as_experience():
    edu_only = "Education\nB.Tech Computer Science, 2019 - 2023"
    exp_section = "Software Intern, Jan 2023 - Jun 2023"
    assert experience.estimate_years_experience(edu_only, exp_section) == 0.4


def test_overlapping_roles_counted_once():
    text = "Engineer, Jan 2018 - Jan 2022\nFreelance, Jan 2020 - Jan 2021"
    assert experience.estimate_years_experience(text) == 4.0
