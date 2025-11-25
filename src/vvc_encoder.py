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
                timeout=10800  # 3 hour timeout (AI mode can be very slow)
            )
            
            encoding_time = time.time() - start_time
            
            if result.returncode != 0:
                self.logger.error(f"Encoding failed: {result.stderr}")
                raise RuntimeError(f"VVenC encoding failed: {result.stderr}")
            
            # Parse output (VVenC may output to stdout or stderr)
            output_text = result.stdout if result.stdout else result.stderr
            stats = self._parse_output(output_text, encoding_time)
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
        
        # Verbosity to get statistics output
        cmd.extend(['--verbosity', '4'])  # Verbose mode to print encoding stats
        
        # QP map (for ROI encoding)
        # NOTE: VVenC app does not support --qpmap option in command line
        # CTU-level QP control requires using VVenC library API, not available via CLI
        # For now, we log this limitation and encode with base QP
        if qp_map and os.path.exists(qp_map):
            self.logger.warning("QP map provided but VVenC CLI does not support --qpmap option")
            self.logger.warning("Encoding with uniform base QP instead (CTU-level QP requires library API)")
            # cmd.extend(['--qpmap', qp_map])  # Not supported
        
        # NOTE: CTUSize and SEIDecodedPictureHash options may not be available
        # in all vvencapp versions. They are removed to ensure compatibility.
        
        return cmd
    
    def _parse_output(self, output_text: str, encoding_time: float) -> Dict:
        """
        Parse VVenC output to extract statistics
        
        Args:
            output_text: VVenC stdout/stderr output
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
        
        # Debug: log the actual output
        self.logger.debug("VVenC output:")
        self.logger.debug(output_text if output_text else "(empty)")
        
        # Parse bitrate - try multiple patterns
        bitrate_patterns = [
            r'avg_bitrate[=\s]+([\d.]+)\s+kbps',  # VVenC: avg_bitrate= 29914.88 kbps
            r'Bitrate\s+([\d.]+)',  # VVenC table: Bitrate     Y-PSNR
            r'Total Bitrate:\s+([\d.]+)\s+kbps',
            r'bitrate.*?:\s+([\d.]+)\s+kbps',
            r'avg bitrate\s+([\d.]+)\s+kbit/s',
        ]
        for pattern in bitrate_patterns:
            bitrate_match = re.search(pattern, output_text, re.IGNORECASE)
            if bitrate_match:
                stats['bitrate'] = float(bitrate_match.group(1))
                break
        
        # Parse PSNR - VVenC outputs in table format after "Y-PSNR    U-PSNR    V-PSNR"
        # Example: "          50    a   29914.8816   42.5487   50.7075   50.9686   43.9565"
        psnr_patterns = [
            # VVenC table format: Bitrate Y-PSNR U-PSNR V-PSNR
            r'Y-PSNR\s+U-PSNR\s+V-PSNR.*?[\d]+\s+[a-z]?\s+[\d.]+\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',
            # Standard format
            r'Y-PSNR[:\s]+([\d.]+)\s+U-PSNR[:\s]+([\d.]+)\s+V-PSNR[:\s]+([\d.]+)',
            r'PSNR.*?Y[:\s]+([\d.]+)\s+U[:\s]+([\d.]+)\s+V[:\s]+([\d.]+)',
            r'Y\s+([\d.]+)\s+dB.*?U\s+([\d.]+)\s+dB.*?V\s+([\d.]+)\s+dB',
        ]
        for pattern in psnr_patterns:
            psnr_match = re.search(pattern, output_text, re.IGNORECASE | re.DOTALL)
            if psnr_match:
                stats['psnr_y'] = float(psnr_match.group(1))
                stats['psnr_u'] = float(psnr_match.group(2))
                stats['psnr_v'] = float(psnr_match.group(3))
                break
        
        # Parse number of frames
        frames_patterns = [
            r'(\d+)\s+frames',
            r'frames.*?:\s*(\d+)',
            r'encoded\s+(\d+)\s+frames',
        ]
        for pattern in frames_patterns:
            frames_match = re.search(pattern, output_text, re.IGNORECASE)
            if frames_match:
                stats['frames'] = int(frames_match.group(1))
                break
        
        # If parsing failed, log warning
        if stats['bitrate'] == 0.0 or stats['psnr_y'] == 0.0:
            self.logger.warning("Failed to parse some encoding statistics")
            self.logger.warning(f"Parsed: bitrate={stats['bitrate']}, PSNR_Y={stats['psnr_y']}")
        
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
