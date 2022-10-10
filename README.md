# A tool for automating _studoš's_ boring tasks

Note: currently, only FER _materijali_ downloading is implemented. Suggest ideas in issues.

Prerequisites:
- install python poetry package manager
- [download webdriver binaries](https://chromedriver.chromium.org/downloads) for your version of browser
- configure environment variables with your FER Intranet credentials in example `.example.env` file
- install dependencies with `poetry install`

## Download _materijali_
To download all available _materijali_ from FER Intranet, call following script:
```bash
materijali
```

Verified to work on Chromium/Mac but should work just fine on any platform combo. If you find any issues,
feel free to open a Github issue. PRs are also welcome.