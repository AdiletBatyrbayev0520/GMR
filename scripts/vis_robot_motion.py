from general_motion_retargeting import RobotMotionViewer, load_robot_motion
import argparse
import pathlib
import os
from tqdm import tqdm


def visualize_single(robot_type, motion_path, record_video, video_path, loop):
    motion_data, motion_fps, motion_root_pos, motion_root_rot, motion_dof_pos, \
        motion_local_body_pos, motion_link_body_list = load_robot_motion(motion_path)

    env = RobotMotionViewer(
        robot_type=robot_type,
        motion_fps=motion_fps,
        camera_follow=False,
        record_video=record_video,
        video_path=str(video_path),
    )

    frame_idx = 0
    while True:
        env.step(
            motion_root_pos[frame_idx],
            motion_root_rot[frame_idx],
            motion_dof_pos[frame_idx],
            rate_limit=True,
        )
        frame_idx += 1
        if frame_idx >= len(motion_root_pos):
            if loop:
                frame_idx = 0
            else:
                break

    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", type=str, default="unitree_g1")
    parser.add_argument(
        "--robot_motion_path",
        type=str,
        required=True,
        help="Path to a .pkl file or a folder of .pkl files.",
    )
    parser.add_argument("--record_video", action="store_true")
    parser.add_argument(
        "--video_path",
        type=str,
        default="videos/example.mp4",
        help="Output .mp4 file (single-file mode) or output folder (folder mode).",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=False,
        help="Loop the motion (single-file mode only).",
    )
    parser.add_argument(
        "--override",
        action="store_true",
        default=False,
        help="Re-render videos that already exist (folder mode).",
    )

    args = parser.parse_args()

    input_path = pathlib.Path(args.robot_motion_path)

    # ── Folder mode ──────────────────────────────────────────────────────────
    if input_path.is_dir():
        pkl_files = sorted(input_path.rglob("*.pkl"))
        if not pkl_files:
            raise FileNotFoundError(f"No .pkl files found in {input_path}")

        out_dir = pathlib.Path(args.video_path)
        print(f"Found {len(pkl_files)} pkl file(s) in {input_path}")

        for pkl_path in tqdm(pkl_files, desc="Rendering"):
            rel = pkl_path.relative_to(input_path)
            out_video = out_dir / rel.with_suffix(".mp4")

            if out_video.exists() and not args.override:
                tqdm.write(f"Skip {rel} (video exists, use --override to re-render)")
                continue

            os.makedirs(out_video.parent, exist_ok=True)
            tqdm.write(f"Rendering {rel} → {out_video}")
            try:
                visualize_single(
                    robot_type=args.robot,
                    motion_path=pkl_path,
                    record_video=True,
                    video_path=out_video,
                    loop=False,
                )
            except Exception as e:
                tqdm.write(f"Error processing {rel}: {e}")

    # ── Single-file mode ─────────────────────────────────────────────────────
    else:
        if not input_path.exists():
            raise FileNotFoundError(f"Motion file not found: {input_path}")

        visualize_single(
            robot_type=args.robot,
            motion_path=input_path,
            record_video=args.record_video,
            video_path=args.video_path,
            loop=args.loop,
        )
