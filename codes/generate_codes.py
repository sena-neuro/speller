import numpy as np
import pyntbci

# Generate m-sequence
codes = pyntbci.stimulus.shift(pyntbci.stimulus.make_m_sequence())
np.savez("shifted_m_sequence.npz", codes=codes)

# Generate Gold codes
codes = pyntbci.stimulus.modulate(pyntbci.stimulus.make_gold_codes())
np.savez("modulated_gold_codes.npz", codes=codes)
