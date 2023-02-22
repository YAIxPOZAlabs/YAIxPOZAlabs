from . import corruption, download, preprocess, wrapper
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import *
    import os


# usage: from data import load_data_text
def load_data_music(
        split: "str|list|tuple" = 'train',
        batch_size: "Optional[int]" = 1,
        data_dir: "Union[str, os.PathLike]" = None,
        use_corruption: bool = False,
        corr_available: "str|list|tuple" = None,
        corr_max: "str|int" = None,
        corr_p: "str|float" = None,
        use_bucketing: bool = True,
        seq_len: "Optional[int]" = None,
        deterministic: bool = False,
        loop: bool = True,
        num_preprocess_proc: int = 4,
        num_loader_proc: int = 0,
):
    """
For a dataset, create a generator over (seqs, kwargs) pairs.

Each seq is an (bsz, len, h) float tensor, and the kwargs dict contains zero or
more keys, each of which map to a batched Tensor of their own.
The kwargs dict can be used for some meta information.

:param split: how to split data - train, or valid.
:param batch_size: the batch size of each returned pair.
:param data_dir: data directory.
:param use_corruption: if True, corruption will be applied input_ids by configs below.
:param corr_available: available corruptions.
:param corr_max: max number of corruptions.
:param corr_p: probability to choice each corruption.
:param use_bucketing: if True, padding will be optimized by each batch.
:param seq_len: default sequence length to pad when not using bucketing.
:param deterministic: if True, yield results in a deterministic order.
:param loop: loop to get batch data or not.
    if loop is True - infinite iterator will be returned
    if loop is False - default iterator will be returned
    if loop is None - raw dataloader will be returned
:param num_preprocess_proc: num of worker while tokenizing.
:param num_loader_proc: num of worker for data loader.
"""
    if isinstance(split, (list, tuple)):
        kw = locals().copy()
        split = kw.pop('split')
        return [load_data_music(split=sp, **kw) for sp in split]

    from .preprocess import tokenize_with_caching
    from .wrapper import wrap_dataset
    from .corruption import Corruptions

    if use_corruption:
        corruption_fn = Corruptions.from_config(
            corr_available=corr_available,
            corr_max=corr_max,
            corr_p=corr_p
        )
    else:
        corruption_fn = None
    tokenized_data = tokenize_with_caching(
        data_dir=data_dir,
        split=split,
        num_proc=num_preprocess_proc,
    )
    data_loader = wrap_dataset(
        tokenized_data,
        batch_size=batch_size,
        use_bucketing=use_bucketing,
        seq_len=seq_len,
        deterministic=deterministic,
        corruption=corruption_fn,
        num_preprocess_proc=num_preprocess_proc,
        num_loader_proc=num_loader_proc
    )
    if loop:
        return _infinite_loader(data_loader)
    else:
        return data_loader


def _infinite_loader(iterable):
    while True:
        yield from iterable
