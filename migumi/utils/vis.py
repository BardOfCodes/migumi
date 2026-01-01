
import numpy as np
from matplotlib.colors import Normalize
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from PIL import Image
import io
from typing import List, Literal
from geolipi.torch_compute import recursive_evaluate
from migumi.torch_compute.polyline_utils import set_bounds_by_expr, get_bounds_by_expr
from PIL import Image, ImageChops


def draw_solid_overlay(output, res, color='blue', boundary_color='black', boundary_width=2.0, figsize=(6, 6)):
    """
    Draws a solid filled region with a boundary contour, transparent outside for overlaying.

    Parameters:
    - output (torch.Tensor or np.ndarray): 2D array of data values (reshaped if needed).
    - res (int): Resolution used to reshape the output if it's flattened.
    - color: Fill color for the inside region (any matplotlib color format).
    - boundary_color: Color for the boundary line. Default is 'black'.
    - boundary_width (float): Line width for the boundary. Default is 2.0.
    - figsize (tuple): Figure size. Default is (6, 6).

    Returns:
    - fig (matplotlib.figure.Figure): The generated figure object with transparent background.
    """
    if hasattr(output, 'cpu'):
        output = output.reshape(res, res, 1).cpu().numpy()
    z = output[:, :, 0]

    fig, ax = plt.subplots(figsize=figsize)
    
    # Make figure and axes background transparent
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    
    # Create RGBA image: fill inside (z < 0) with color, outside is transparent
    from matplotlib.colors import to_rgba
    rgba_color = to_rgba(color)
    
    # Create an RGBA array
    rgba_image = np.zeros((z.shape[0], z.shape[1], 4))
    inside_mask = z < 0
    rgba_image[inside_mask] = rgba_color  # Fill inside with the specified color
    # Outside remains [0, 0, 0, 0] (transparent)
    
    ax.imshow(rgba_image, origin='lower', aspect='equal')
    
    # Draw only the boundary contour at level 0
    ax.contour(z, levels=[0], colors=[boundary_color], linewidths=boundary_width, origin='lower')
    
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    fig.tight_layout()
    
    return fig


def draw_contour_plot(output, res, 
    colormap='coolwarm', solid_inside=False, figsize=(6, 6),
    add_colorbar=True, levelrate=10 ):
    """
    Draws a contour plot with improved color mapping and optional solid inside rendering.

    Parameters:
    - output (torch.Tensor or np.ndarray): 2D array of data values (reshaped if needed).
    - res (int): Resolution used to reshape the output if it's flattened.
    - colormap (str): Matplotlib colormap name for smooth transitions.
    - solid_inside (bool): If True, renders negative values as a flat color.

    Returns:
    - fig (matplotlib.figure.Figure): The generated figure object.
    """
    if hasattr(output, 'cpu'):
        output = output.reshape(res, res, 1).cpu().numpy()
    z = output[:, :, 0]

    # Define contour levels
    max_val = np.max(z)
    min_val = np.min(z)
    if solid_inside:
        levels = np.linspace(0, max_val, levelrate)
    else:
        levels = np.linspace(min_val, max_val, levelrate)

    # Colormap normalization centered at zero, adjusted from -1 to 1
    norm = Normalize(vmin=-1, vmax=1)
    cmap = cm.get_cmap(colormap)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if solid_inside:
        # Fill negative values with a flat color (middle negative value)
        mid_negative = -0.5  # (min_val + 0) / 2  # Middle of the negative range
        ax.imshow(np.where(z < 0, mid_negative, z), cmap=cmap, norm=norm, origin='lower')  # FIXED: origin='lower'
        
        # Draw only positive contours
        ax.contour(z, levels=levels, colors='black', linewidths=0.5, linestyles='solid', origin='lower')  # FIXED
        ax.contour(z, colors='black', levels=[0], linewidths=2.5, origin='lower')  # FIXED
    else:
        # Regular contour plot with color transitions
        contour = ax.contourf(z, levels=levels, cmap=cmap, norm=norm, alpha=0.9)
        if add_colorbar:
            fig.colorbar(contour, ax=ax, shrink=0.8, pad=0.02)
        ax.contour(z, levels=levels, colors='black', linewidths=0.5, linestyles='solid', origin='lower')  # FIXED
        ax.contour(z, colors='black', levels=[0], linewidths=2.5, origin='lower')  # FIXED
    
    # Ensure the plot is a proper square
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    fig.tight_layout()
    
    return fig


def fig_to_image(fig) -> Image.Image:
    """Convert a matplotlib figure to a PIL Image."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    img = Image.open(buf).convert('RGBA')
    plt.close(fig)
    return img


def frames_to_animation(
    frames: List[Image.Image],
    output_path: str,
    fps: int = 10,
    format: Literal['gif', 'webp', 'mp4'] = 'gif',
    mp4_quality: Literal['lossless', 'high', 'medium'] = 'high',
) -> str:
    """
    Takes a sequence of PIL Image frames and saves them as an animated GIF, WebP, or MP4.

    Parameters:
    - frames (List[Image.Image]): List of PIL Image frames.
    - output_path (str): Path where the animation file will be saved.
    - fps (int): Frames per second for the animation. Default is 10.
    - format (str): Output format: 'gif', 'webp', or 'mp4'. Default is 'gif'.
    - mp4_quality (str): Quality for MP4 encoding. Only used when format='mp4'.
        - 'lossless': No compression (CRF 0, very large files)
        - 'high': Visually lossless (CRF 17, recommended for quality)
        - 'medium': Good quality with smaller file size (CRF 23)

    Returns:
    - str: The path to the saved animation file.
    """
    if not frames:
        raise ValueError("No frames provided")
    
    # Ensure all frames have the same size (resize to first frame's size)
    base_size = frames[0].size
    frames = [f.resize(base_size, Image.Resampling.LANCZOS) if f.size != base_size else f 
              for f in frames]
    
    # Calculate duration in milliseconds
    duration_ms = int(1000 / fps)
    
    # Ensure correct file extension
    if not output_path.lower().endswith(f'.{format}'):
        output_path = f"{output_path}.{format}"
    
    # Save animation
    if format == 'gif':
        # Convert RGBA to P mode for better GIF support
        frames_p = [f.convert('P', palette=Image.Palette.ADAPTIVE, colors=256) for f in frames]
        frames_p[0].save(
            output_path,
            save_all=True,
            append_images=frames_p[1:],
            duration=duration_ms,
            loop=0,  # 0 = infinite loop
            optimize=True
        )
    elif format == 'webp':
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            lossless=True
        )
    elif format == 'mp4':
        import imageio.v3 as iio
        import numpy as np
        
        # CRF values: 0 = lossless, 17 = visually lossless, 23 = default
        crf_map = {'lossless': 0, 'high': 17, 'medium': 23}
        crf = crf_map.get(mp4_quality, 17)
        
        # Convert PIL Images to numpy arrays (RGB, not RGBA for MP4)
        frame_arrays = [np.array(f.convert('RGB')) for f in frames]
        
        # Build ffmpeg output parameters for high quality
        if mp4_quality == 'lossless':
            # Use FFV1 codec for truly lossless, or x264 with crf=0
            codec = 'libx264'
            output_params = [
                '-crf', '0',
                '-preset', 'veryslow',
                '-pix_fmt', 'yuv444p',  # No chroma subsampling for lossless
            ]
        else:
            codec = 'libx264'
            output_params = [
                '-crf', str(crf),
                '-preset', 'slow',  # Better compression at cost of encoding time
                '-pix_fmt', 'yuv420p',  # Standard compatibility
                '-profile:v', 'high',
                '-level', '4.2',
            ]
        
        iio.imwrite(
            output_path,
            frame_arrays,
            fps=fps,
            codec=codec,
            output_params=output_params,
        )
    
    return output_path


def expressions_to_animation(
    expressions: List,
    sketcher,
    output_path: str,
    fps: int = 10,
    format: Literal['gif', 'webp', 'mp4'] = 'gif',
    mp4_quality: Literal['lossless', 'high', 'medium'] = 'high',
    scale_multiplier: float = 2.0,
    colormap: str = 'coolwarm',
    solid_inside: bool = True,
    figsize_scale: float = 3.0,
) -> str:
    """
    Takes a sequence of expressions, evaluates each to generate contour plots,
    and saves them as an animated GIF, WebP, or MP4.

    Parameters:
    - expressions (List): List of expression objects that can be evaluated.
    - sketcher: A Sketcher instance for coordinate creation and evaluation.
    - output_path (str): Path where the animation file will be saved.
    - fps (int): Frames per second for the animation. Default is 10.
    - format (str): Output format: 'gif', 'webp', or 'mp4'. Default is 'gif'.
    - mp4_quality (str): Quality for MP4 encoding ('lossless', 'high', 'medium').
    - scale_multiplier (float): Multiplier for the scale bounds. Default is 2.0.
    - colormap (str): Matplotlib colormap name. Default is 'coolwarm'.
    - solid_inside (bool): If True, renders negative values as flat color. Default is True.
    - figsize_scale (float): Scale factor for figure size based on bounds. Default is 3.0.

    Returns:
    - str: The path to the saved animation file.
    """
    frames = []
    
    for expr in expressions:
        # Get tensor representation
        design = expr.tensor()
        
        # Set and get bounds
        set_bounds_by_expr(design, sketcher)
        scale, origin = get_bounds_by_expr(design, sketcher)
        scale = [x * scale_multiplier for x in scale]
        
        # Create non-square coordinates
        coords, shape = sketcher.create_non_square_coords(scale, origin)
        coords = coords.float()
        
        # Evaluate the expression
        output = recursive_evaluate(design, sketcher, coords=coords)
        output = output.cpu().numpy()
        output = output.reshape(shape)[..., None]
        
        # Calculate figsize based on scale
        figsize = (scale[1] * figsize_scale, scale[0] * figsize_scale)
        
        # Generate the contour plot figure
        fig = draw_contour_plot(output, sketcher.resolution, figsize=figsize, 
                                colormap=colormap, solid_inside=solid_inside)
        
        # Convert figure to PIL Image and store
        frame = fig_to_image(fig)
        fig.close()
        frames.append(frame)
    
    return frames_to_animation(frames, output_path, fps=fps, format=format, mp4_quality=mp4_quality)

def overlay_image(
    base: Image.Image,
    top: Image.Image,
    position=(0, 0),
    mode="normal",   # "normal", "multiply", "screen", "add", etc.
    opacity=1.0
) -> Image.Image:
    """
    Return a new image with `top` composited over `base` at `position`.
    """
    # Ensure RGBA
    base = base.convert("RGBA")
    top = top.convert("RGBA")

    # Apply opacity (like SVG opacity)
    if opacity < 1.0:
        alpha = top.split()[-1].point(lambda a: int(a * opacity))
        top.putalpha(alpha)

    # Create a canvas so we can position the top
    canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    canvas.paste(top, position, mask=top)

    if mode == "normal":
        # SVG-style normal alpha compositing
        out = Image.alpha_composite(base, canvas)

    else:
        # Do blend like SVG blend modes using ImageChops on RGB,
        # then reapply alpha
        base_rgb = base.convert("RGB")
        canvas_rgb = canvas.convert("RGB")

        if mode == "multiply":
            blended_rgb = ImageChops.multiply(base_rgb, canvas_rgb)
        elif mode == "screen":
            blended_rgb = ImageChops.screen(base_rgb, canvas_rgb)
        elif mode == "add":
            blended_rgb = ImageChops.add(base_rgb, canvas_rgb)
        elif mode == "subtract":
            blended_rgb = ImageChops.subtract(base_rgb, canvas_rgb)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Use alpha from normal composite for correct transparency
        alpha_comp = Image.alpha_composite(base, canvas)
        out = Image.merge("RGBA", (*blended_rgb.split(), alpha_comp.split()[-1]))

    return out