"""
GOP (Group of Pictures) Manager
Handles GOP structure for different VVC configurations (AI, RA, LDP)
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class FrameType(Enum):
    """Frame types in video coding"""
    I = "I"  # Intra frame
    P = "P"  # Predicted frame
    B = "B"  # Bidirectional frame


@dataclass
class FrameInfo:
    """Information about a frame in GOP structure"""
    index: int  # Frame index in sequence
    type: FrameType  # Frame type (I, P, B)
    poc: int  # Picture Order Count
    temporal_layer: int  # Temporal layer (0 = highest priority)
    qp_offset: int  # QP offset for this frame
    ref_frames: List[int]  # Reference frame indices
    is_keyframe: bool  # Whether to run detector on this frame


class GOPManager:
    """
    Manages GOP structure for different VVC configurations
    """
    
    def __init__(self, config: Dict):
        """
        Initialize GOP Manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.encoder_config = config['encoder']
        self.gop_size = self.encoder_config['gop_size']
        self.intra_period = self.encoder_config['intra_period']
        self.config_type = self.encoder_config['config']  # AI, RA, LDP
        
        # Temporal propagation settings
        self.temporal_config = config['roi_detection']['temporal']
        self.keyframe_interval = self.temporal_config.get('keyframe_interval', self.gop_size)
        
    def generate_frame_structure(self, n_frames: int) -> List[FrameInfo]:
        """
        Generate frame structure for entire sequence
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            List of FrameInfo objects
        """
        if self.config_type == "AI":
            return self._generate_ai_structure(n_frames)
        elif self.config_type == "RA":
            return self._generate_ra_structure(n_frames)
        elif self.config_type == "LDP":
            return self._generate_ldp_structure(n_frames)
        else:
            raise ValueError(f"Unknown config type: {self.config_type}")
    
    def _generate_ai_structure(self, n_frames: int) -> List[FrameInfo]:
        """
        Generate All-Intra structure (all frames are I-frames)
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            List of FrameInfo objects
        """
        frames = []
        for i in range(n_frames):
            frame = FrameInfo(
                index=i,
                type=FrameType.I,
                poc=i,
                temporal_layer=0,
                qp_offset=0,
                ref_frames=[],
                is_keyframe=True  # All frames are keyframes in AI
            )
            frames.append(frame)
        return frames
    
    def _generate_ra_structure(self, n_frames: int) -> List[FrameInfo]:
        """
        Generate Random Access structure with hierarchical B-frames
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            List of FrameInfo objects
        """
        frames = []
        
        # QP offsets for hierarchical levels (from config or default)
        qp_offsets = self.encoder_config.get('qp_offset_list', [1, 2, 3, 4])
        
        for gop_start in range(0, n_frames, self.intra_period):
            gop_end = min(gop_start + self.intra_period, n_frames)
            
            # First frame of GOP is I-frame
            frames.append(FrameInfo(
                index=gop_start,
                type=FrameType.I,
                poc=gop_start,
                temporal_layer=0,
                qp_offset=0,
                ref_frames=[],
                is_keyframe=True
            ))
            
            # Generate hierarchical B-frames
            for mini_gop_start in range(gop_start + 1, gop_end, self.gop_size):
                mini_gop_end = min(mini_gop_start + self.gop_size, gop_end)
                mini_gop_frames = self._generate_hierarchical_b_frames(
                    mini_gop_start, mini_gop_end, qp_offsets
                )
                frames.extend(mini_gop_frames)
        
        # Sort by POC for display order
        frames.sort(key=lambda x: x.poc)
        
        return frames
    
    def _generate_hierarchical_b_frames(self, 
                                       start: int, 
                                       end: int,
                                       qp_offsets: List[int]) -> List[FrameInfo]:
        """
        Generate hierarchical B-frame structure for a mini-GOP
        
        Args:
            start: Start frame index
            end: End frame index
            qp_offsets: QP offsets for each temporal layer
            
        Returns:
            List of FrameInfo objects
        """
        frames = []
        n_frames = end - start
        
        if n_frames <= 0:
            return frames
        
        # Calculate number of temporal layers
        n_layers = int(np.log2(self.gop_size)) + 1
        
        # Generate frames in coding order (hierarchical)
        self._add_hierarchical_frames(
            frames, start, end, 0, n_layers, qp_offsets
        )
        
        return frames
    
    def _add_hierarchical_frames(self,
                                frames: List[FrameInfo],
                                start: int,
                                end: int,
                                layer: int,
                                max_layers: int,
                                qp_offsets: List[int]) -> None:
        """
        Recursively add hierarchical B-frames
        
        Args:
            frames: List to append frames to
            start: Start frame index
            end: End frame index
            layer: Current temporal layer
            max_layers: Maximum number of layers
            qp_offsets: QP offsets for each layer
        """
        if start >= end or layer >= max_layers:
            return
        
        # Middle frame at current layer
        mid = (start + end) // 2
        
        if mid < end:
            # Determine if this is a keyframe for detection
            is_keyframe = (mid % self.keyframe_interval == 0)
            
            # Get QP offset for this layer
            qp_offset = qp_offsets[min(layer, len(qp_offsets) - 1)]
            
            # Add middle frame
            frames.append(FrameInfo(
                index=mid,
                type=FrameType.B,
                poc=mid,
                temporal_layer=layer,
                qp_offset=qp_offset,
                ref_frames=[start - 1, end] if start > 0 else [end],
                is_keyframe=is_keyframe
            ))
            
            # Recursively add frames in left and right halves
            self._add_hierarchical_frames(
                frames, start, mid, layer + 1, max_layers, qp_offsets
            )
            self._add_hierarchical_frames(
                frames, mid + 1, end, layer + 1, max_layers, qp_offsets
            )
    
    def _generate_ldp_structure(self, n_frames: int) -> List[FrameInfo]:
        """
        Generate Low-Delay P structure
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            List of FrameInfo objects
        """
        frames = []
        
        for i in range(n_frames):
            if i % self.intra_period == 0:
                # I-frame
                frame = FrameInfo(
                    index=i,
                    type=FrameType.I,
                    poc=i,
                    temporal_layer=0,
                    qp_offset=0,
                    ref_frames=[],
                    is_keyframe=True
                )
            else:
                # P-frame
                is_keyframe = (i % self.keyframe_interval == 0)
                frame = FrameInfo(
                    index=i,
                    type=FrameType.P,
                    poc=i,
                    temporal_layer=0,
                    qp_offset=0,
                    ref_frames=[i - 1],
                    is_keyframe=is_keyframe
                )
            frames.append(frame)
        
        return frames
    
    def get_keyframe_indices(self, n_frames: int) -> List[int]:
        """
        Get indices of frames where detector should run
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            List of keyframe indices
        """
        frame_structure = self.generate_frame_structure(n_frames)
        return [f.index for f in frame_structure if f.is_keyframe]
    
    def get_gop_boundaries(self, n_frames: int) -> List[Tuple[int, int]]:
        """
        Get GOP boundaries (start, end) for the sequence
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            List of (start, end) tuples
        """
        boundaries = []
        
        if self.config_type == "AI":
            # Each frame is its own GOP
            for i in range(n_frames):
                boundaries.append((i, i + 1))
        else:
            # Regular GOP structure
            for start in range(0, n_frames, self.gop_size):
                end = min(start + self.gop_size, n_frames)
                boundaries.append((start, end))
        
        return boundaries
    
    def get_reference_frames(self, frame_idx: int, n_frames: int) -> List[int]:
        """
        Get reference frame indices for a given frame
        
        Args:
            frame_idx: Frame index
            n_frames: Total number of frames
            
        Returns:
            List of reference frame indices
        """
        frame_structure = self.generate_frame_structure(n_frames)
        
        for frame in frame_structure:
            if frame.index == frame_idx:
                return frame.ref_frames
        
        return []
    
    def print_structure(self, n_frames: int) -> None:
        """
        Print GOP structure for debugging
        
        Args:
            n_frames: Total number of frames
        """
        frames = self.generate_frame_structure(n_frames)
        
        print(f"\n{'='*80}")
        print(f"GOP Structure: {self.config_type}")
        print(f"GOP Size: {self.gop_size}, Intra Period: {self.intra_period}")
        print(f"Keyframe Interval: {self.keyframe_interval}")
        print(f"{'='*80}")
        print(f"{'Index':<8} {'Type':<6} {'POC':<6} {'Layer':<8} {'QP Offset':<10} {'Refs':<15} {'Keyframe'}")
        print(f"{'-'*80}")
        
        for frame in frames[:min(len(frames), 50)]:  # Show first 50 frames
            refs_str = str(frame.ref_frames) if frame.ref_frames else "[]"
            print(f"{frame.index:<8} {frame.type.value:<6} {frame.poc:<6} "
                  f"{frame.temporal_layer:<8} {frame.qp_offset:<10} "
                  f"{refs_str:<15} {'Yes' if frame.is_keyframe else 'No'}")
        
        if len(frames) > 50:
            print(f"... ({len(frames) - 50} more frames)")
        
        print(f"{'='*80}\n")
