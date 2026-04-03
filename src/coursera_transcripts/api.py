import time
import requests
from urllib.parse import urljoin

from rich.console import Console


COURSERA_BASE = "https://www.coursera.org"
COURSERA_VERSION = "e184c443bbe09b70cbcebf2ba22b3b1067d7e119"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "*/*",
    "Accept-Language": "en",
    "X-Coursera-Application": "ondemand",
    "X-Coursera-Version": COURSERA_VERSION,
    "X-Requested-With": "XMLHttpRequest",
}


def _build_headers(cookie: str, referer: str | None = None) -> dict:
    headers = HEADERS.copy()
    headers["Cookie"] = cookie
    if referer:
        headers["Referer"] = referer
    return headers


class CourseAPI:
    def __init__(self, cookie: str, console: Console | None = None):
        self.cookie = cookie
        self.session = requests.Session()
        self.console = console or Console()

    def _get(self, url: str, referer: str | None = None, max_retries: int = 3) -> requests.Response:
        headers = _build_headers(self.cookie, referer)
        last_exception: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt == max_retries - 1:
                    break
                wait = 2 ** attempt
                self.console.print(
                    f"  [warning]⟳  Request failed, retrying in {wait}s…[/warning] [muted]({e})[/muted]"
                )
                time.sleep(wait)
        raise last_exception  # type: ignore[misc]

    def get_course_materials(self, slug: str) -> dict:
        url = (
            f"{COURSERA_BASE}/api/onDemandCourseMaterials.v2/"
            f"?q=slug&slug={slug}"
            f"&includes=modules%2Clessons%2CpassableItemGroups%2CpassableItemGroupChoices%2CpassableLessonElements%2Citems%2Ctracks%2CgradePolicy%2CgradingParameters%2CembeddedContentMapping"
            f"&fields=moduleIds%2ConDemandCourseMaterialModules.v1(name%2Cslug%2Cdescription%2CtimeCommitment%2ClessonIds%2Coptional%2ClearningObjectives)%2ConDemandCourseMaterialLessons.v1(name%2Cslug%2CtimeCommitment%2CelementIds%2Coptional%2CtrackId)%2ConDemandCourseMaterialPassableItemGroups.v1(requiredPassedCount%2CpassableItemGroupChoiceIds%2CtrackId)%2ConDemandCourseMaterialPassableItemGroupChoices.v1(name%2Cdescription%2CitemIds)%2ConDemandCourseMaterialPassableLessonElements.v1(gradingWeight%2CisRequiredForPassing)%2ConDemandCourseMaterialItems.v2(name%2CoriginalName%2Cslug%2CtimeCommitment%2CcontentSummary%2CisLocked%2ClockableByItem%2CitemLockedReasonCode%2CtrackId%2ClockedStatus%2CitemLockSummary%2CcustomDisplayTypenameOverride)%2ConDemandCourseMaterialTracks.v1(passablesCount)%2ConDemandGradingParameters.v1(gradedAssignmentGroups)%2CcontentAtomRelations.v1(embeddedContentSourceCourseId%2CsubContainerId)"
            f"&showLockedItems=true"
        )
        referer = f"{COURSERA_BASE}/learn/{slug}/home/module/1"
        response = self._get(url, referer)
        data = response.json()

        if not data.get("elements"):
            raise ValueError(f"Course '{slug}' not found or no data returned")

        return data

    def get_lecture_video(self, course_id: str, item_id: str) -> dict:
        url = (
            f"{COURSERA_BASE}/api/onDemandLectureVideos.v1/"
            f"{course_id}~{item_id}"
            f"?includes=video"
            f"&fields=onDemandVideos.v1(sources%2Csubtitles%2CsubtitlesTxt%2CsubtitlesAssetTags%2CdubbedSources%2CdubbedSubtitlesVtt%2CaudioDescriptionVideoSources)"
            f"%2CdisableSkippingForward%2CstartMs%2CendMs"
        )
        response = self._get(url)
        return response.json()

    def download_subtitle(self, relative_url: str) -> str:
        url = urljoin(COURSERA_BASE, relative_url)
        response = self._get(url)
        return response.text
