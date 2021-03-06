# Copyright 2018 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests that application of operations works correctly in the plugin devices"""
import pytest

import numpy as np
import pennylane as qml
from scipy.linalg import block_diag

from conftest import U, U2, A

np.random.seed(42)


# ==========================================================
# Some useful global variables

# non-parametrized qubit gates
I = np.identity(2)
X = np.array([[0, 1], [1, 0]])
Y = np.array([[0, -1j], [1j, 0]])
Z = np.array([[1, 0], [0, -1]])
H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
S = np.diag([1, 1j])
T = np.diag([1, np.exp(1j * np.pi / 4)])
SWAP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
CZ = np.diag([1, 1, 1, -1])
toffoli = np.diag([1 for i in range(8)])
toffoli[6:8, 6:8] = np.array([[0, 1], [1, 0]])
CSWAP = block_diag(I, I, SWAP)

# parametrized qubit gates
phase_shift = lambda phi: np.array([[1, 0], [0, np.exp(1j * phi)]])
rx = lambda theta: np.cos(theta / 2) * I + 1j * np.sin(-theta / 2) * X
ry = lambda theta: np.cos(theta / 2) * I + 1j * np.sin(-theta / 2) * Y
rz = lambda theta: np.cos(theta / 2) * I + 1j * np.sin(-theta / 2) * Z
rot = lambda a, b, c: rz(c) @ (ry(b) @ rz(a))
crz = lambda theta: np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, np.exp(-1j * theta / 2), 0],
        [0, 0, 0, np.exp(1j * theta / 2)],
    ]
)

# list of all non-parametrized single-qubit gates,
# along with the PennyLane operation name
single_qubit = [
    ("PauliX", X),
    ("PauliY", Y),
    ("PauliZ", Z),
    ("Hadamard", H),
    ("S", S),
    ("Sdg", S.conj().T),
    ("T", T),
    ("Tdg", T.conj().T),
]

# list of all parametrized single-qubit gates
single_qubit_param = [("PhaseShift", phase_shift), ("RX", rx), ("RY", ry), ("RZ", rz)]
# list of all non-parametrized two-qubit gates
two_qubit = [("CNOT", CNOT), ("SWAP", SWAP), ("CZ", CZ)]
# list of all parametrized two-qubit gates
two_qubit_param = [("CRZ", crz)]
# list of all three-qubit gates
three_qubit = [("Toffoli", toffoli), ("CSWAP", CSWAP)]


def reverse_state(state):
    N = int(np.log2(len(state)))
    return state.reshape([2] * N).T.flatten()


@pytest.mark.parametrize("shots", [0])
class TestStateApply:
    """Test application of PennyLane operations to state simulators."""

    def test_basis_state(self, device, tol):
        """Test basis state initialization"""
        dev = device(4)
        state = np.array([0, 0, 1, 0])

        dev.apply("BasisState", [0, 1, 2, 3], [state])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2

        expected = np.zeros([2 ** 4])
        expected[np.ravel_multi_index(state, [2] * 4)] = 1
        expected = reverse_state(expected)

        assert np.allclose(res, expected, **tol)

    def test_identity_basis_state(self, device, tol):
        """Test basis state initialization if identity"""
        dev = device(4)
        state = np.array([1, 0, 0, 0])

        dev.apply("BasisState", [0, 1, 2, 3], [state])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2

        expected = np.zeros([2 ** 4])
        expected[np.ravel_multi_index(state, [2] * 4)] = 1
        expected = reverse_state(expected)

        assert np.allclose(res, expected, **tol)

    def test_qubit_state_vector(self, init_state, device, tol):
        """Test PauliX application"""
        dev = device(1)
        state = init_state(1)

        dev.apply("QubitStateVector", [0], [state])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(state) ** 2
        assert np.allclose(res, expected, **tol)

    def test_invalid_qubit_state_vector(self, device):
        """Test that an exception is raised if the state
        vector is the wrong size"""
        dev = device(2)
        state = np.array([0, 123.432])

        with pytest.raises(ValueError, match=r"State vector must be of length 2\*\*wires"):
            dev.apply("QubitStateVector", [0, 1], [state])

    @pytest.mark.parametrize("name,mat", single_qubit)
    def test_single_qubit_no_parameters(self, init_state, device, name, mat, tol):
        """Test PauliX application"""
        dev = device(1)
        state = init_state(1)

        dev.apply("QubitStateVector", [0], [state])
        dev.apply(name, [0], [])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("theta", [0.5432, -0.232])
    @pytest.mark.parametrize("name,func", single_qubit_param)
    def test_single_qubit_parameters(self, init_state, device, name, func, theta, tol):
        """Test PauliX application"""
        dev = device(1)
        state = init_state(1)

        dev.apply("QubitStateVector", [0], [state])
        dev.apply(name, [0], [theta])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(func(theta) @ state) ** 2
        assert np.allclose(res, expected, **tol)

    def test_rotation(self, init_state, device, tol):
        """Test three axis rotation gate"""
        dev = device(1)
        state = init_state(1)

        a = 0.542
        b = 1.3432
        c = -0.654

        dev.apply("QubitStateVector", [0], [state])
        dev.apply("Rot", [0], [a, b, c])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(rot(a, b, c) @ state) ** 2

        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("name,mat", two_qubit)
    def test_two_qubit_no_parameters(self, init_state, device, name, mat, tol):
        """Test PauliX application"""
        dev = device(2)
        state = init_state(2)

        dev.apply("QubitStateVector", [0, 1], [state])
        dev.apply(name, [0, 1], [])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("mat", [U, U2])
    def test_qubit_unitary(self, init_state, device, mat, tol):
        N = int(np.log2(len(mat)))
        dev = device(N)
        state = init_state(N)

        dev.apply("QubitStateVector", list(range(N)), [state])
        dev.apply("QubitUnitary", list(range(N)), [mat])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    def test_invalid_qubit_state_unitary(self, device):
        """Test that an exception is raised if the
        unitary matrix is the wrong size"""
        dev = device(2)
        state = np.array([[0, 123.432], [-0.432, 023.4]])

        with pytest.raises(ValueError, match=r"Unitary matrix must be of shape"):
            dev.apply("QubitUnitary", [0, 1], [state])

    @pytest.mark.parametrize("name, mat", three_qubit)
    def test_three_qubit_no_parameters(self, init_state, device, name, mat, tol):
        dev = device(3)
        state = init_state(3)

        dev.apply("QubitStateVector", [0, 1, 2], [state])
        dev.apply("QubitUnitary", [0, 1, 2], [mat])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("theta", [0.5432, -0.232])
    @pytest.mark.parametrize("name,func", two_qubit_param)
    def test_single_qubit_parameters(self, init_state, device, name, func, theta, tol):
        """Test PauliX application"""
        dev = device(2)
        state = init_state(2)

        dev.apply("QubitStateVector", [0, 1], [state])
        dev.apply(name, [0, 1], [theta])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.abs(dev.state) ** 2
        expected = np.abs(func(theta) @ state) ** 2
        assert np.allclose(res, expected, **tol)


@pytest.mark.parametrize("shots", [8192])
class TestHardwareApply:
    """Test application of PennyLane operations on hardware simulators."""

    def test_basis_state(self, device, tol):
        """Test basis state initialization"""
        dev = device(4)
        state = np.array([0, 0, 1, 0])

        dev.apply("BasisState", [0, 1, 2, 3], [state])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)

        expected = np.zeros([2 ** 4])
        expected[np.ravel_multi_index(state, [2] * 4)] = 1
        assert np.allclose(res, expected, **tol)

    def test_basis_state_not_first_operation(self, device):
        """Test that an exception is raised if BasisState is
        applied to a circuit not in the ground state"""
        dev = device(4)
        state = np.array([0, 0, 1, 0])

        dev.apply("Hadamard", [0], [])

        with pytest.raises(
            qml.DeviceError, match="annot be used after other Operations have already been applied"
        ):
            dev.apply("BasisState", [0, 1, 2, 3], [state])

    def test_qubit_state_vector(self, init_state, device, tol):
        """Test PauliX application"""
        dev = device(1)
        state = init_state(1)

        dev.apply("QubitStateVector", [0], [state])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(state) ** 2
        assert np.allclose(res, expected, **tol)

    def test_invalid_qubit_state_vector(self, device):
        """Test that an exception is raised if the state
        vector is the wrong size"""
        dev = device(2)
        state = np.array([0, 123.432])

        with pytest.raises(ValueError, match=r"State vector must be of length 2\*\*wires"):
            dev.apply("QubitStateVector", [0, 1], [state])

    @pytest.mark.parametrize("name,mat", single_qubit)
    def test_single_qubit_no_parameters(self, init_state, device, name, mat, tol):
        """Test PauliX application"""
        dev = device(1)
        state = init_state(1)

        dev.apply("QubitStateVector", [0], [state])
        dev.apply(name, [0], [])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("theta", [0.5432, -0.232])
    @pytest.mark.parametrize("name,func", single_qubit_param)
    def test_single_qubit_parameters(self, init_state, device, name, func, theta, tol):
        """Test PauliX application"""
        dev = device(1)
        state = init_state(1)

        dev.apply("QubitStateVector", [0], [state])
        dev.apply(name, [0], [theta])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(func(theta) @ state) ** 2
        assert np.allclose(res, expected, **tol)

    def test_rotation(self, init_state, device, tol):
        """Test three axis rotation gate"""
        dev = device(1)
        state = init_state(1)

        a = 0.542
        b = 1.3432
        c = -0.654

        dev.apply("QubitStateVector", [0], [state])
        dev.apply("Rot", [0], [a, b, c])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(rot(a, b, c) @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("name,mat", two_qubit)
    def test_two_qubit_no_parameters(self, init_state, device, name, mat, tol):
        """Test PauliX application"""
        dev = device(2)
        state = init_state(2)

        dev.apply("QubitStateVector", [0, 1], [state])
        dev.apply(name, [0, 1], [])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("mat", [U, U2])
    def test_qubit_unitary(self, init_state, device, mat, tol):
        N = int(np.log2(len(mat)))
        dev = device(N)
        state = init_state(N)

        dev.apply("QubitStateVector", list(range(N)), [state])
        dev.apply("QubitUnitary", list(range(N)), [mat])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    def test_invalid_qubit_state_unitary(self, device):
        """Test that an exception is raised if the
        unitary matrix is the wrong size"""
        dev = device(2)
        state = np.array([[0, 123.432], [-0.432, 023.4]])

        with pytest.raises(ValueError, match=r"Unitary matrix must be of shape"):
            dev.apply("QubitUnitary", [0, 1], [state])

    @pytest.mark.parametrize("name, mat", three_qubit)
    def test_three_qubit_no_parameters(self, init_state, device, name, mat, tol):
        dev = device(3)
        state = init_state(3)

        dev.apply("QubitStateVector", [0, 1, 2], [state])
        dev.apply("QubitUnitary", [0, 1, 2], [mat])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(mat @ state) ** 2
        assert np.allclose(res, expected, **tol)

    @pytest.mark.parametrize("theta", [0.5432, -0.232])
    @pytest.mark.parametrize("name,func", two_qubit_param)
    def test_single_qubit_parameters(self, init_state, device, name, func, theta, tol):
        """Test PauliX application"""
        dev = device(2)
        state = init_state(2)

        dev.apply("QubitStateVector", [0, 1], [state])
        dev.apply(name, [0, 1], [theta])
        dev._obs_queue = []
        dev.pre_measure()

        res = np.fromiter(dev.probabilities().values(), dtype=np.float64)
        expected = np.abs(func(theta) @ state) ** 2
        assert np.allclose(res, expected, **tol)
