<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
<!-- [![Contributors][contributors-shield]][contributors-url] -->
<!-- [![Forks][forks-shield]][forks-url] -->
<!-- [![Stargazers][stars-shield]][stars-url] -->
<!-- [![Issues][issues-shield]][issues-url] -->
<!-- [![MIT License][license-shield]][license-url] -->
<!-- [![LinkedIn][linkedin-shield]][linkedin-url] -->



<!-- PROJECT LOGO -->
<br />
<div align="center">

<h3 align="center">Demo2Code</h3>

  <p align="center">
    This is an official implementation for the NeurIPS 2023 paper:
    <br />
    <strong>Demo2Code: From Summarizing Demonstrations to Synthesizing Code via Extended Chain-of-Thought</strong>
    <br />
    <br />
    <a href="https://lunay0yuki.github.io/">Huaxiaoyue (Yuki) Wang</a>
    ·
    <a href="https://github.com/chalo2000">Gonzalo Gonzalez-Pumariega</a>
    ·
    <a href="https://yash-s20.github.io/">Yash Sharma</a>
    .
    <a href="https://www.sanjibanchoudhury.com/">Sanjiban Choudhury</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#getting-started">Installation</a>
      <ul>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#navigating-the-repo">Navigating the Repo</a></li>
      </ul>
    </li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li>
        <a href="#detailed-usage">Detailed Usage</a>
        <ul>
        <li><a href="#part-1-generate-code">Part 1: Generate Code</a></li>
        <li><a href="#part-2-execute-code">Part 2: Execute Code</a></li>
        <li><a href="#part-3-evaluate">Part 3: Evaluate</a></li>
        </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>


## Getting Started

### Installation

1. Create the conda env from yaml file
```
conda create -n demo2code python=3.8.16
```
2. Clone the robotouille repo somewhere on your computer (Not in this repo!)

https://github.com/portal-cornell/robotouille/tree/main

3. cd into robotouille's folder. check out to `git checkout 4190a1deabcd108320e6e4c694ba7fad55ea5b76`

4. activate the conda env: `conda activate demo2code`

5. run `pip install -e .`

6. cd back to this repo. run `pip install -r requirements.txt`

#### Install assets for tabletop environment
Go to folder `data/tabletop/env_setup_data` and run the following commands:
```bash
gdown --id 1Cc_fDSBL6QiDvNT4dpfAEbhbALSVoWcc
gdown --id 1yOMEm-Zp_DL3nItG9RozPeJAmeOldekX
gdown --id 1GsqNLhEl9dd4Mc3BM0dX3MibOI1FVWNM

unzip ur5e.zip
unzip robotiq_2f_85.zip
unzip bowl.zip
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Navigating the Repo
* `data` contains the demonstrations and the prompt files. For each domain, there are folders for:
  * `demonstration_config` contains
    * `_demo-config.txt` which contains the list of tasks to run an approach on (to generate code)
    * `_test-time_demo-config.txt` which contains the list of tasks to run the code generated by the approach on (to evaluate the code)
  * `demonstration` contains the demonstrations for each approach
  * `prompt` contains the prompt files for each approach
* `outputs` contains the output when running the experiments. For each domain, there are folders for:
  * `cot` contains the output of the recursive summarization (only for demo2code and demonolang2code)
  * `code` contains the generated code
  * `state` contains the generated states after running the code (only for robotouille and tabletop)
  * `eval_result` contains the evaluation results
  * `env-info` contains the environment information (used for evaluation). This is not saved on the repo, but is generated when running the experiments.
* `scripts` contains the main python files to run the experiments
  * main demo2code algorithm is in `scripts/overall_helpers/code_gen_helper.py`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Quick Start
A quick start guide for gonzalo:

You can run everything
```bash
python main.py ROBOTOUILLE --model_names demo2code --render
```

Alternatively, if you just want to render the code
```bash
python scripts/robotouille_main.py --model_names demo2code --render
```

A couple of things you need to make sure:
- In data/robotouille/prompt/demo2code/demo2code_prompt.yaml, you need to verify the prompt_version. 
  - This prompt_version affects what folder the results get stored. 
  - For example, the generated states will be stored under outputs/robotouille/state/demo2code/{prompt_version}
- To modify what tasks get run/tested, you should modify data/robotouille/demonstration_config/latest-test-time_demo-config.txt.
  - here "latest" correspond to the demo_version.
  - this affects what demo gets loaded/used in data/robotouille/demonstration/demo2code/{demo_version}
  - to change demo_version (not recommended), you can use the argument `--demo_version` when you run the python file
```bash
python scripts/robotouille_main.py --demo_version {put_your_demo_version_here} --model_names demo2code --render
```
<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

Yuki Wang - yukiwang@cs.cornell.edu

Paper Project Link: [https://portal-cornell.github.io/demo2code-webpage/](https://portal-cornell.github.io/demo2code-webpage/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

We thank [Nicole Thean (@nicolethean)](https://github.com/nicolethean) for her help with creating the assets that bring Robotouille to life!

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/portal-cornell/simple-gpt.svg?style=for-the-badge
[contributors-url]: https://github.com/portal-cornell/simple-gpt/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/portal-cornell/simple-gpt.svg?style=for-the-badge
[forks-url]: https://github.com/portal-cornell/simple-gpt/network/members
[stars-shield]: https://img.shields.io/github/stars/portal-cornell/simple-gpt.svg?style=for-the-badge
[stars-url]: https://github.com/portal-cornell/simple-gpt/stargazers
[issues-shield]: https://img.shields.io/github/issues/portal-cornell/simple-gpt.svg?style=for-the-badge
[issues-url]: https://github.com/portal-cornell/simple-gpt/issues
[license-shield]: https://img.shields.io/github/license/portal-cornell/simple-gpt.svg?style=for-the-badge
[license-url]: https://github.com/portal-cornell/simple-gpt/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com 