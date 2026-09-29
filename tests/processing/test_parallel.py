from app.processing.parallel import ParallelProcessor


def square(x: int) -> int:
    return x * x


def test_parallel_processor():

    values = [1, 2, 3, 4, 5]

    results = ParallelProcessor.process(
        values,
        square,
    )

    assert results == [1, 4, 9, 16, 25]