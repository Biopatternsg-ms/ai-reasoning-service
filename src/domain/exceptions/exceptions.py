#
# Copyright © 2026 biopatternsg (biopatternsg@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
class DomainException(Exception):
    """Base exception for all domain-related errors in ai-reasoning-service."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AlignmentException(DomainException):
    """Raised when an error occurs during the biological alignment evaluation."""
    pass


class EntityValidationException(DomainException):
    """Raised when biological entity data is malformed or invalid."""
    pass
