import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

const Banglear = () => {
  const containerRef = useRef();
  const imgRef = useRef();
  const wristCoordinates = useRef({ x: -0.2, y: -0.0, z: -0.2, yaw: 0, pitch: 0, roll: 0, width: 0 });
  const [videoFeedLoaded, setVideoFeedLoaded] = useState(false);

  let scene, camera, renderer, bangleModel;
  const apiEndpoint = "http://127.0.0.1:5000/get_wrist_coordinates";
  const videoFeedEndpoint = "http://127.0.0.1:5000/video-feed";

  const initScene = () => {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, imgRef.current.width / imgRef.current.height, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(imgRef.current.width, imgRef.current.height);
    renderer.setClearColor(0x000000, 0);
    containerRef.current.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 10, 7.5);
    scene.add(directionalLight);

    const loader = new GLTFLoader();
    loader.load("/model/scene.gltf", (gltf) => {
      bangleModel = gltf.scene;
      bangleModel.scale.set(0.05, 0.05, 0.05);
      bangleModel.position.set(0, -0.05, -0.2);
      scene.add(bangleModel);
    });
  };

  const fetchWristCoordinates = async () => {
    try {
      const response = await fetch(apiEndpoint);
      if (!response.ok) throw new Error("Failed to fetch wrist coordinates");

      const data = await response.json();
      if (data?.wrists?.length > 0) {
        const wrist = data.wrists[0];
        wristCoordinates.current = {
          x: smoothWrist(wrist.x),
          y: smoothWrist(wrist.y),
          z: wrist.z !== undefined ? -0.5 * wrist.z : -0.2,
          yaw: wrist.yaw || 0,
          pitch: wrist.pitch || 0,
          roll: wrist.roll || 0,
          width: wrist.width ? wrist.width * 0.005 : 1,
        };
      }
    } catch (error) {
      console.error("Error fetching wrist coordinates:", error);
    }
  };

  let prevPositions = [];
  const smoothWrist = (newPos) => {
    prevPositions.push(newPos);
    if (prevPositions.length > 5) prevPositions.shift();
    return prevPositions.reduce((sum, val) => sum + val, 0) / prevPositions.length;
  };

  const animate = () => {
    requestAnimationFrame(animate);
    if (bangleModel) {
      const videoWidth = imgRef.current.naturalWidth || imgRef.current.width;
      const videoHeight = imgRef.current.naturalHeight || imgRef.current.height;

      const normalizedX = (wristCoordinates.current.x / videoWidth) * 2 - 1;
      const normalizedY = -(wristCoordinates.current.y / videoHeight) * 2 + 1;

      const dx = Math.abs(normalizedX - bangleModel.position.x);
      const dy = Math.abs(normalizedY - bangleModel.position.y);

      let newX = bangleModel.position.x;
      let newY = bangleModel.position.y;

      if (dx > dy) {
        newX = normalizedX;
      } else {
        newY = normalizedY;
      }

      const targetVector = new THREE.Vector3(newX, newY, -0.2);
      targetVector.unproject(camera);
      bangleModel.position.lerp(targetVector, 0.15);

      // **Fixed Bounding Box**
      const boundingBox = {
        xMin: -0.1,
        xMax: 0.1,
        yMin: -0.1,
        yMax: 0.1,
        zMin: -0.3,
        zMax: -0.1,
      };

      if (
        bangleModel.position.x > boundingBox.xMin &&
        bangleModel.position.x < boundingBox.xMax &&
        bangleModel.position.y > boundingBox.yMin &&
        bangleModel.position.y < boundingBox.yMax &&
        bangleModel.position.z > boundingBox.zMin &&
        bangleModel.position.z < boundingBox.zMax
      ) {
        bangleModel.visible = false;
      } else {
        bangleModel.visible = true;
      }

      const scaleValue = Math.max(0.02, Math.min(wristCoordinates.current.width, 0.07));
      bangleModel.scale.set(scaleValue, scaleValue, scaleValue);

      const { yaw, pitch, roll } = wristCoordinates.current;
      bangleModel.rotation.set(-pitch, Math.PI / 2 + yaw, roll);

      renderer.render(scene, camera);
    }
  };

  useEffect(() => {
    if (imgRef.current && imgRef.current.src !== videoFeedEndpoint) {
      imgRef.current.src = videoFeedEndpoint;
    }

    imgRef.current.onload = () => {
      setVideoFeedLoaded(true);
      initScene();
      animate();
    };

    const intervalId = setInterval(fetchWristCoordinates, 100);

    return () => {
      clearInterval(intervalId);
      if (renderer) renderer.dispose();
    };
  }, []);

  return (
    <div style={{ position: "relative", width: "100%", height: "100vh" }}>
      {!videoFeedLoaded && <div className="loading">Loading AR...</div>}
      <img
        ref={imgRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
        alt="Webcam Feed"
      />
      <div
        ref={containerRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          pointerEvents: "none",
        }}
      ></div>

      {/* Bounding Box */}
      {/* Bounding Box (Shifted to bottom-center) */}
        {/* Expanded Bounding Box (taller and wider) */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "75%", // slightly moved up to balance increased height
            width: "250px", // doubled from 120px
            height: "200px", // doubled from 40px
            border: "2px solid red",
            transform: "translate(-50%, -50%)",
            borderRadius: "6px",
            zIndex: 10,
          }}
        ></div>

        {/* Instruction Text (Above the box) */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "73%", // Slightly above the box
            transform: "translate(-50%, -50%)",
            color: "white",
            fontSize: "16px",
            fontWeight: "bold",
            backgroundColor: "rgba(0, 0, 0, 0.7)",
            padding: "5px 10px",
            borderRadius: "5px",
            zIndex: 10,
          }}
        >
          Keep your hand straight, parallel to the camera, in the box.And try to Keep your wrist outside the red box, for perfect fit the bangle on wrist .
        </div>
    </div>
  );
};

export default Banglear;
