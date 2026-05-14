import argparse
import pathlib
import pickle
import time
import os
import numpy as np
from rich import print
from tqdm import tqdm

from general_motion_retargeting import GeneralMotionRetargeting as GMR
from general_motion_retargeting import RobotMotionViewer
from general_motion_retargeting.utils.lafan1 import load_bvh_file


def save_motion(qpos_list, motion_fps, save_path):
    root_pos = np.array([q[:3] for q in qpos_list])
    root_rot = np.array([q[3:7][[1, 2, 3, 0]] for q in qpos_list])  # wxyz → xyzw
    dof_pos  = np.array([q[7:] for q in qpos_list])
    motion_data = {
        "fps": motion_fps,
        "root_pos": root_pos,
        "root_rot": root_rot,
        "dof_pos": dof_pos,
        "local_body_pos": None,
        "link_body_list": None,
    }
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    with open(save_path, "wb") as f:
        pickle.dump(motion_data, f)
    print(f"Saved to {save_path}")


def retarget_single(bvh_file, args, retargeter=None):
    frames, human_height = load_bvh_file(bvh_file, format=args.format)

    if retargeter is None:
        retargeter = GMR(
            src_human=f"bvh_{args.format}",
            tgt_robot=args.robot,
            actual_human_height=human_height,
        )

    qpos_list = []
    for frame in tqdm(frames, desc=f"Retargeting {pathlib.Path(bvh_file).name}"):
        qpos_list.append(retargeter.retarget(frame))

    return qpos_list, retargeter


def run_single_with_viewer(bvh_file, args):
    frames, human_height = load_bvh_file(bvh_file, format=args.format)

    retargeter = GMR(
        src_human=f"bvh_{args.format}",
        tgt_robot=args.robot,
        actual_human_height=human_height,
    )

    viewer = RobotMotionViewer(
        robot_type=args.robot,
        motion_fps=args.motion_fps,
        transparent_robot=0,
        record_video=args.record_video,
        video_path=args.video_path,
    )

    fps_counter = 0
    fps_start = time.time()
    pbar = tqdm(total=len(frames), desc="Retargeting")
    qpos_list = [] if args.save_path else None

    i = 0
    while True:
        fps_counter += 1
        now = time.time()
        if now - fps_start >= 2.0:
            print(f"Actual rendering FPS: {fps_counter / (now - fps_start):.2f}")
            fps_counter = 0
            fps_start = now

        pbar.update(1)
        qpos = retargeter.retarget(frames[i])

        viewer.step(
            root_pos=qpos[:3],
            root_rot=qpos[3:7],
            dof_pos=qpos[7:],
            human_motion_data=retargeter.scaled_human_data,
            rate_limit=args.rate_limit,
            follow_camera=True,
        )

        if qpos_list is not None:
            qpos_list.append(qpos)

        if args.loop:
            i = (i + 1) % len(frames)
        else:
            i += 1
            if i >= len(frames):
                break

    pbar.close()
    viewer.close()

    if args.save_path and qpos_list:
        save_motion(qpos_list, args.motion_fps, args.save_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bvh_file",
        help="BVH file or folder of BVH files to process.",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--format",
        choices=["lafan1", "nokov"],
        default="lafan1",
    )
    parser.add_argument(
        "--loop",
        default=False,
        action="store_true",
        help="Loop the motion (single-file mode only).",
    )
    parser.add_argument(
        "--robot",
        choices=["unitree_g1", "unitree_g1_with_hands", "booster_t1", "stanford_toddy",
                 "fourier_n1", "engineai_pm01", "pal_talos"],
        default="unitree_g1",
    )
    parser.add_argument("--record_video", action="store_true", default=False)
    parser.add_argument("--video_path", type=str, default="videos/example.mp4")
    parser.add_argument("--rate_limit", action="store_true", default=False)
    parser.add_argument(
        "--save_path",
        default=None,
        help="Output .pkl file (single-file mode) or output folder (folder mode).",
    )
    parser.add_argument("--motion_fps", default=30, type=int)
    parser.add_argument(
        "--override",
        action="store_true",
        default=False,
        help="Re-process files even if the output already exists (folder mode).",
    )

    args = parser.parse_args()

    input_path = pathlib.Path(args.bvh_file)

    # ── Folder mode ──────────────────────────────────────────────────────────
    if input_path.is_dir():
        if args.save_path is None:
            raise ValueError("--save_path is required when --bvh_file is a folder.")

        out_dir = pathlib.Path(args.save_path)
        bvh_files = sorted(input_path.rglob("*.bvh"))
        if not bvh_files:
            raise FileNotFoundError(f"No .bvh files found in {input_path}")

        print(f"Found {len(bvh_files)} BVH file(s) in [cyan]{input_path}[/cyan]")

        retargeter = None  # reuse across files
        for bvh_path in tqdm(bvh_files, desc="Files"):
            rel = bvh_path.relative_to(input_path)
            out_path = out_dir / rel.with_suffix(".pkl")

            if out_path.exists() and not args.override:
                print(f"[yellow]Skip[/yellow] {rel} (output exists, use --override to reprocess)")
                continue

            try:
                qpos_list, retargeter = retarget_single(bvh_path, args, retargeter)
                save_motion(qpos_list, args.motion_fps, out_path)
            except Exception as e:
                print(f"[red]Error[/red] processing {rel}: {e}")

    # ── Single-file mode ─────────────────────────────────────────────────────
    else:
        if not input_path.exists():
            raise FileNotFoundError(f"BVH file not found: {input_path}")

        run_single_with_viewer(str(input_path), args)
