"""
VVC Encoder Module
Wrapper for VVenC (Fraunhofer Versatile Video Encoder)
Reference: https://github.com/fraunhoferhhi/vvenc
"""

import subprocess
import os
import re
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import logging
import tempfile


class VVCEncoder:
    """
    VVenC Encoder Wrapper
    Provides interface to VVenC encoder with QP map support
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize VVC Encoder
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.encoder_config = config['encoder']
        self.logger = logger or logging.getLogger(__name__)
        
        # Encoder settings
        self.software = self.encoder_config.get('software', 'vvenc')
        self.preset = self.encoder_config.get('preset', 'medium')
        self.threads = self.encoder_config.get('threads', 8)
        self.config_type = self.encoder_config.get('config', 'AI')
        self.gop_size = self.encoder_config.get('gop_size', 16)
        self.intra_period = self.encoder_config.get('intra_period', 32)
        self.frame_rate = self.encoder_config.get('frame_rate', 30)
        self.ctu_size = self.encoder_config.get('ctu_size', 128)
        
        # Find vvencapp executable
        self.vvenc_path = self._find_vvenc()
        
        self.logger.info(f"VVC Encoder initialized: {self.vvenc_path}")
    
    def _find_vvenc(self) -> str:
        """
        Find vvencapp executable
        
        Returns:
            Path to vvencapp
        """
        # Check common locations
        possible_paths = [
            'vvencapp',  # In PATH
            'vvencapp.exe',  # Windows in PATH
            os.path.expanduser('~/vvenc/build/bin/release-static/vvencapp'),  # Linux
            os.path.expanduser('~/vvenc/build/bin/Release/vvencapp.exe'),  # Windows
            'C:/vvenc/build/bin/Release/vvencapp.exe',  # Windows alternative
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        raise FileNotFoundError(
            "vvencapp not found. Please install VVenC:\n"
            "  Linux/Mac: bash scripts/install_vvenc.sh\n"
            "  Windows: scripts\\install_vvenc.bat\n"
            "Or add vvencapp to PATH"
        )
    
    def encode(self,
               input_file: str,
               output_file: str,
               qp: int,
               qp_map: Optional[str] = None,
               width: Optional[int] = None,
               height: Optional[int] = None) -> Dict:
        """
        Encode video with VVenC
        
        Args:
            input_file: Input video file (YUV or image sequence)
            output_file: Output bitstream file (.266)
            qp: Base QP value
            qp_map: Optional QP map file for ROI encoding
            width: Video width (required for YUV)
            height: Video height (required for YUV)
            
        Returns:
            Dictionary with encoding results
        """
        # Build command
        cmd = self._build_command(
            input_file, output_file, qp, qp_map, width, height
        )
        
        self.logger.info(f"Encoding: {input_file} -> {output_file}")
        self.logger.debug(f"Command: {' '.join(cmd)}")
        
        # Run encoding
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            encoding_time = time.time() - start_time
            
            if result.returncode != 0:
                self.logger.error(f"Encoding failed: {result.stderr}")
                raise RuntimeError(f"VVenC encoding failed: {result.stderr}")
            
            # Parse output
            stats = self._parse_output(result.stderr, encoding_time)
            stats['output_file'] = output_file
            
            self.logger.info(
                f"Encoded: {stats['bitrate']:.2f} kbps, "
                f"{stats['encoding_time']:.2f}s, "
                f"PSNR: {stats['psnr_y']:.2f} dB"
            )
            
            return stats
            
        except subprocess.TimeoutExpired:
            self.logger.error("Encoding timeout (1 hour)")
            raise RuntimeError("Encoding timeout")
    
    def _build_command(self,
                      input_file: str,
                      output_file: str,
                      qp: int,
                      qp_map: Optional[str],
                      width: Optional[int],
                      height: Optional[int]) -> List[str]:
        """
        Build VVenC command line
        
        Returns:
            Command as list of strings
        """
        cmd = [self.vvenc_path]
        
        # Input/Output
        cmd.extend(['-i', input_file])
        cmd.extend(['-o', output_file])
        
        # Size (required for YUV input)
        if width and height:
            cmd.extend(['-s', f'{width}x{height}'])
        
        # QP
        cmd.extend(['-q', str(qp)])
        
        # Frame rate
        cmd.extend(['-r', str(self.frame_rate)])
        
        # Preset
        cmd.extend(['--preset', self.preset])
        
        # Configuration (AI, RA, LDP)
        if self.config_type == 'AI':
            cmd.extend(['--IntraPeriod', '1'])
        elif self.config_type == 'RA':
            cmd.extend(['--IntraPeriod', str(self.intra_period)])
            cmd.extend(['--GOPSize', str(self.gop_size)])
        elif self.config_type == 'LDP':
            cmd.extend(['--IntraPeriod', str(self.intra_period)])
            cmd.extend(['--GOPSize', str(self.gop_size)])
            cmd.extend(['--LowDelay', '1'])
        
        # Threads
        cmd.extend(['--threads', str(self.threads)])
        
        # QP map (for ROI encoding)
        if qp_map and os.path.exists(qp_map):
            cmd.extend(['--qpmap', qp_map])
        
        # NOTE: CTUSize and SEIDecodedPictureHash options may not be available
        # in all vvencapp versions. They are removed to ensure compatibility.
        
        return cmd
    
    def _parse_output(self, stderr: str, encoding_time: float) -> Dict:
        """
        Parse VVenC output to extract statistics
        
        Args:
            stderr: VVenC stderr output
            encoding_time: Measured encoding time
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'encoding_time': encoding_time,
            'bitrate': 0.0,
            'psnr_y': 0.0,
            'psnr_u': 0.0,
            'psnr_v': 0.0,
            'frames': 0,
        }
        
        # Parse bitrate
        bitrate_match = re.search(r'Total Bitrate:\s+([\d.]+)\s+kbps', stderr)
        if bitrate_match:
            stats['bitrate'] = float(bitrate_match.group(1))
        
        # Parse PSNR
        psnr_match = re.search(r'PSNR Y:\s+([\d.]+)\s+U:\s+([\d.]+)\s+V:\s+([\d.]+)', stderr)
        if psnr_match:
            stats['psnr_y'] = float(psnr_match.group(1))
            stats['psnr_u'] = float(psnr_match.group(2))
            stats['psnr_v'] = float(psnr_match.group(3))
        
        # Parse number of frames
        frames_match = re.search(r'(\d+)\s+frames', stderr)
        if frames_match:
            stats['frames'] = int(frames_match.group(1))
        
        return stats
    
    def encode_with_qp_map(self,
                          input_file: str,
                          output_file: str,
                          base_qp: int,
                          qp_map_array: 'np.ndarray',
                          width: int,
                          height: int) -> Dict:
        """
        Encode video with CTU-level QP map
        
        Args:
            input_file: Input video file
            output_file: Output bitstream
            base_qp: Base QP value
            qp_map_array: QP map array (n_ctu_h, n_ctu_w)
            width: Video width
            height: Video height
            
        Returns:
            Encoding statistics
        """
        # Create temporary QP map file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            qp_map_file = f.name
            self._write_qp_map_file(f, qp_map_array)
        
        try:
            # Encode with QP map
            stats = self.encode(
                input_file, output_file, base_qp,
                qp_map=qp_map_file,
                width=width, height=height
            )
            return stats
        finally:
            # Clean up temporary file
            if os.path.exists(qp_map_file):
                os.remove(qp_map_file)
    
    def _write_qp_map_file(self, f, qp_map_array: 'np.ndarray') -> None:
        """
        Write QP map to file in VVenC format
        
        Args:
            f: File handle
            qp_map_array: QP map array (n_ctu_h, n_ctu_w)
        """
        n_ctu_h, n_ctu_w = qp_map_array.shape
        
        # Write header
        f.write(f"# QP Map for VVenC\n")
        f.write(f"# CTU size: {self.ctu_size}x{self.ctu_size}\n")
        f.write(f"# Grid: {n_ctu_h}x{n_ctu_w}\n")
        f.write(f"\n")
        
        # Write QP values
        for i in range(n_ctu_h):
            for j in range(n_ctu_w):
                qp = int(qp_map_array[i, j])
                f.write(f"{qp} ")
            f.write("\n")
    
    def get_encoder_info(self) -> Dict:
        """
        Get encoder information
        
        Returns:
            Dictionary with encoder info
        """
        try:
            result = subprocess.run(
                [self.vvenc_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            version_match = re.search(r'vvencapp:\s+([\d.]+)', result.stdout)
            version = version_match.group(1) if version_match else 'unknown'
            
            return {
                'software': 'VVenC',
                'version': version,
                'path': self.vvenc_path,
                'preset': self.preset,
                'config': self.config_type,
                'threads': self.threads,
            }
        except Exception as e:
            self.logger.error(f"Failed to get encoder info: {e}")
            return {'software': 'VVenC', 'version': 'unknown'}
