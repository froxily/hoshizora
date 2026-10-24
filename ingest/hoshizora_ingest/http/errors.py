class SourceHttpError(Exception):
    def __init__(self, status: int, url: str, *, duration_ms: int) -> None:
        super().__init__(f"HTTP {status} from {url}")
        self.status = status
        self.url = url
        self.duration_ms = duration_ms


class RetryableHttpError(SourceHttpError):
    def __init__(
        self, status: int, url: str, retry_after: float | None, *, duration_ms: int
    ) -> None:
        super().__init__(status, url, duration_ms=duration_ms)
        self.retry_after = retry_after


class QuotaExhaustedError(RetryableHttpError):
    pass


class NeedsReviewError(SourceHttpError):
    pass


class WaitLimitExceededError(Exception):
    def __init__(self, seconds: float, limit: float) -> None:
        super().__init__(f"Would wait {seconds:.0f} s, over the {limit:.0f} s limit")
        self.seconds = seconds
        self.limit = limit


class RequestBudgetExhaustedError(Exception):
    def __init__(self, budget: int) -> None:
        super().__init__(f"Request budget of {budget} used up")
        self.budget = budget
